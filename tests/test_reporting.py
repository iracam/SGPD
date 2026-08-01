"""Fase 9: indicadores do painel (RF-034, RF-035) e relatórios (RF-036)."""

# ruff: noqa: F811

from __future__ import annotations

from datetime import timedelta
from typing import Any
from unittest import mock

import pytest
from django.core.exceptions import ValidationError
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.accounts.models import User
from apps.offboarding.models import OffboardingProcess, ProcessSectorTask, ProcessStatus
from apps.reporting.models import ExportDataset, ReportExport
from apps.sectors.models import SectorResponsible
from tests.test_offboarding_release import release, second_coordinator
from tests.test_offboarding_start import (  # noqa: F401
    PASSWORD,
    actor,
    configured_draft,
    process,
    start,
)
from tests.test_offboarding_tasks import complete_task, start_task, started_task
from tests.test_pending_amounts import (
    analysis_task,
    create_value_pending,
    decide_amount,
    enable_amounts,
    register_amount,
)
from tests.test_pending_items_evidence import create_pending

pytestmark = pytest.mark.django_db

DASHBOARD_URL = "/api/v1/reporting/dashboard/"


def logged_client(user: User) -> Client:
    client = Client()
    assert client.login(username=user.username, password=PASSWORD)
    return client


def dashboard(user: User) -> Any:
    response = logged_client(user).get(DASHBOARD_URL)
    assert response.status_code == 200
    return response.json()


def overdue(task: ProcessSectorTask, *, hours: int = 30) -> ProcessSectorTask:
    task.due_at = timezone.now() - timedelta(hours=hours)
    task.save(update_fields=("due_at",))
    return task


def test_dashboard_counts_the_open_process_and_the_sector_task(
    actor: User,
    process: OffboardingProcess,
) -> None:
    started_task(actor, process)

    body = dashboard(actor)

    coordination = body["coordination"]
    assert coordination["open_processes"] == 1
    assert coordination["completed_processes"] == 0
    assert coordination["overdue_processes"] == 0
    assert coordination["critical_processes"] == []
    # Enum cru não chega ao usuário (ADR-047): o painel já devolve o rótulo.
    assert coordination["by_status"] == [
        {"key": ProcessStatus.STARTED.value, "label": "Iniciado", "total": 1}
    ]
    sector = body["sector"]
    assert sector["pending_tasks"] == 1
    assert sector["overdue_tasks"] == 0
    assert sector["by_company"] == [{"key": "1", "label": "Empresa 1", "total": 1}]
    assert sector["by_branch"][0]["total"] == 1


def test_completed_task_moves_the_process_out_of_the_open_count(
    actor: User,
    process: OffboardingProcess,
) -> None:
    task = started_task(actor, process)
    start_task(actor, task)
    task.refresh_from_db()
    complete_task(actor, task)

    body = dashboard(actor)

    assert body["coordination"]["open_processes"] == 0
    assert body["coordination"]["completed_processes"] == 1
    # A tarefa concluída sai da conta do setor sem sair do processo.
    assert body["sector"]["pending_tasks"] == 0


def test_overdue_task_becomes_delayed_sector_and_critical_process(
    actor: User,
    process: OffboardingProcess,
) -> None:
    task = overdue(started_task(actor, process))
    process.refresh_from_db()
    process.due_date = timezone.localdate() - timedelta(days=1)
    process.save(update_fields=("due_date",))

    body = dashboard(actor)

    coordination = body["coordination"]
    assert coordination["overdue_processes"] == 1
    assert coordination["due_soon_processes"] == 0
    assert coordination["delayed_sectors"] == [
        {"key": str(task.sector_id), "label": task.sector_name_snapshot, "total": 1}
    ]
    critical = coordination["critical_processes"][0]
    assert critical["process_uuid"] == str(process.uuid)
    assert critical["employee_name"] == process.employee_snapshot.employee_name
    assert critical["overdue_tasks"] == 1
    assert body["sector"]["overdue_tasks"] == 1
    assert body["sector"]["critical_processes"][0]["process_uuid"] == str(process.uuid)


def test_the_due_soon_windows_follow_the_notification_marks(
    actor: User,
    process: OffboardingProcess,
) -> None:
    """O painel e o e-mail precisam concordar sobre o que é urgente.

    A janela da tarefa é a de `TAREFA_A_VENCER` (48 h) e a do processo é a de
    `PROCESSO_PROXIMO_LIMITE` (72 h), ambas lidas da mesma configuração que a
    varredura usa (`WORKFLOWS.md` §7).
    """

    task = started_task(actor, process)
    task.due_at = timezone.now() + timedelta(hours=30)
    task.save(update_fields=("due_at",))
    process.refresh_from_db()
    process.due_date = timezone.localdate() + timedelta(days=2)
    process.save(update_fields=("due_date",))

    body = dashboard(actor)

    assert body["sector"]["due_soon_tasks"] == 1
    assert body["sector"]["overdue_tasks"] == 0
    assert body["coordination"]["due_soon_processes"] == 1
    assert body["coordination"]["overdue_processes"] == 0


def test_pending_items_and_amounts_are_counted_until_the_decision(
    actor: User,
    process: OffboardingProcess,
) -> None:
    task = analysis_task(actor, process)
    enable_amounts(task)
    create_pending(actor, task)
    task.refresh_from_db()
    pending_value = create_value_pending(actor, task)
    register_amount(actor, pending_value)

    body = dashboard(actor)

    coordination = body["coordination"]
    assert coordination["open_pending_items"] == 2
    assert coordination["blocking_pending_items"] == 2
    assert coordination["amounts_awaiting_decision"] == 1
    # Dinheiro viaja como string: `float` não é dinheiro.
    assert coordination["amount_totals"] == [{"currency": "BRL", "informed": "1250.00"}]

    pending_value.refresh_from_db()
    decide_amount(second_coordinator(actor), pending_value)

    decided = dashboard(actor)["coordination"]
    assert decided["amounts_awaiting_decision"] == 0
    assert decided["amount_totals"] == []
    # A pendência de material continua aberta e bloqueando.
    assert decided["open_pending_items"] == 1
    assert decided["blocking_pending_items"] == 1


def test_sector_responsible_without_dp_sees_only_the_sector_block(
    actor: User,
    process: OffboardingProcess,
) -> None:
    task = started_task(actor, process)
    responsible = User.objects.create_user(
        username="setor.painel",
        email="setor.painel@example.invalid",
        password=PASSWORD,
    )
    SectorResponsible.objects.create(
        sector_id=task.sector_id,
        user=responsible,
        valid_from=timezone.now() - timedelta(hours=1),
        assigned_by=actor,
        updated_by=actor,
    )

    body = dashboard(responsible)

    assert body["coordination"] is None
    assert body["sector"]["pending_tasks"] == 1


def test_user_without_dp_and_without_sector_sees_no_block(
    actor: User,
    process: OffboardingProcess,
) -> None:
    """Nenhum bloco é informação, não negativa: 403 esconderia o painel de quem
    simplesmente não tem nada a ver."""

    started_task(actor, process)
    outsider = User.objects.create_user(
        username="sem.papel",
        email="sem.papel@example.invalid",
        password=PASSWORD,
    )

    body = dashboard(outsider)

    assert body["coordination"] is None
    assert body["sector"] is None
    assert body["generated_at"]


def test_superadmin_sees_both_blocks_without_assignment(
    actor: User,
    process: OffboardingProcess,
) -> None:
    started_task(actor, process)
    superadmin = User.objects.create_superuser(
        username="super.painel",
        email="super.painel@example.invalid",
        password=PASSWORD,
    )

    body = dashboard(superadmin)

    assert body["coordination"]["open_processes"] == 1
    assert body["sector"]["pending_tasks"] == 1


def test_the_dashboard_never_asks_oracle_to_distinct_a_lob(
    actor: User,
    process: OffboardingProcess,
) -> None:
    """`SELECT DISTINCT` sobre `reason`/`notes` é `ORA-00932` no Oracle.

    O SQLite dos testes aceita, então a suíte passaria enquanto o painel
    quebraria na primeira leitura real — foi exatamente assim que a varredura
    da Fase 7 caiu no DEV. Agrupar sobre a tarefa e resolver o processo por
    subconsulta é o que mantém o `DISTINCT` fora do SQL.
    """

    overdue(started_task(actor, process))
    client = logged_client(actor)

    with CaptureQueriesContext(connection) as captured:
        assert client.get(DASHBOARD_URL).status_code == 200

    statements = [query["sql"].upper() for query in captured.captured_queries]
    assert statements
    assert not [
        sql for sql in statements if "DISTINCT" in sql and "SGPD_OFFBOARDING_PROCESS" in sql
    ]


REPORTS_URL = "/api/v1/reporting/reports/"


def reports(user: User, **params: Any) -> Any:
    response = logged_client(user).get(REPORTS_URL, data=params)
    assert response.status_code == 200
    return response.json()


def test_reports_measure_the_cycle_time_of_process_and_sector(
    actor: User,
    process: OffboardingProcess,
) -> None:
    """Média de duração é calculada em Python de propósito.

    O Oracle guarda a subtração de dois `TIMESTAMP` como `INTERVAL DAY TO
    SECOND` e `AVG` sobre intervalo é `ORA-00932`; o SQLite aceitaria e a suíte
    passaria enquanto o relatório quebraria no DEV.
    """

    task = started_task(actor, process)
    start_task(actor, task)
    task.refresh_from_db()
    complete_task(actor, task)
    task.refresh_from_db()
    concluida = task.completed_at
    assert concluida is not None
    # Doze horas entre o início e a conclusão da tarefa.
    task.started_at = concluida - timedelta(hours=12)
    task.save(update_fields=("started_at",))
    process.refresh_from_db()
    process.started_at = concluida - timedelta(days=4)
    process.save(update_fields=("started_at",))

    body = reports(actor)

    assert body["process_cycle_time"]["processes"] == 1
    assert body["process_cycle_time"]["average_days"] == 4.0
    assert body["process_cycle_time"]["median_days"] == 4.0
    linha = body["sector_cycle_time"][0]
    assert linha["label"] == task.sector_name_snapshot
    assert linha["total"] == 1
    assert linha["average_hours"] == 12.0


def test_reports_group_pendings_companies_and_amounts_in_the_period(
    actor: User,
    process: OffboardingProcess,
) -> None:
    task = analysis_task(actor, process)
    enable_amounts(task)
    create_pending(actor, task)
    task.refresh_from_db()
    register_amount(actor, create_value_pending(actor, task))

    body = reports(actor)

    categorias = {linha["label"]: linha for linha in body["pending_by_category"]}
    assert categorias["Equipamento"]["total"] == 1
    assert categorias["Equipamento"]["detail"] == 1
    assert categorias["Valor"]["total"] == 1
    assert body["processes_by_company"] == [
        {"key": "1", "label": "Empresa 1", "total": 1, "detail": 0}
    ]
    assert body["amounts"] == [
        {"currency": "BRL", "informed": "1250.00", "approved": "0.00", "undecided": 1}
    ]


def test_the_period_filters_the_fact_and_never_the_snapshot_of_delay(
    actor: User,
    process: OffboardingProcess,
) -> None:
    """Atraso não tem data própria: é o estado deste instante.

    Um período antigo esvazia os relatórios de fato ocorrido, mas o processo
    vencido e o setor atrasado continuam aparecendo — quem confere precisa
    saber que existe atraso agora, não em julho passado.
    """

    task = overdue(started_task(actor, process))
    process.refresh_from_db()
    process.due_date = timezone.localdate() - timedelta(days=3)
    process.save(update_fields=("due_date",))
    antigo = (timezone.localdate() - timedelta(days=400)).isoformat()
    quase_antigo = (timezone.localdate() - timedelta(days=390)).isoformat()

    body = reports(actor, start=antigo, end=quase_antigo)

    assert body["processes_by_company"] == []
    assert body["pending_by_category"] == []
    assert body["overdue_processes"]["total"] == 1
    linha = body["overdue_processes"]["results"][0]
    assert linha["process_uuid"] == str(process.uuid)
    assert linha["days_overdue"] == 3
    assert linha["open_tasks"] == 1
    assert body["sector_delays"][0]["label"] == task.sector_name_snapshot
    assert body["sector_delays"][0]["total"] == 1


def test_released_processes_are_grouped_by_month(
    actor: User,
    process: OffboardingProcess,
) -> None:
    task = started_task(actor, process)
    start_task(actor, task)
    task.refresh_from_db()
    complete_task(actor, task)
    process.refresh_from_db()
    release(actor, process)

    body = reports(actor)

    assert body["released_processes"]["total"] == 1
    assert body["released_processes"]["results"][0]["total"] == 1


def test_reports_refuse_the_actor_without_dp(
    actor: User,
    process: OffboardingProcess,
) -> None:
    task = started_task(actor, process)
    responsible = User.objects.create_user(
        username="setor.relatorio",
        email="setor.relatorio@example.invalid",
        password=PASSWORD,
    )
    SectorResponsible.objects.create(
        sector_id=task.sector_id,
        user=responsible,
        valid_from=timezone.now() - timedelta(hours=1),
        assigned_by=actor,
        updated_by=actor,
    )

    response = logged_client(responsible).get(REPORTS_URL)

    assert response.status_code == 403


def test_reports_refuse_an_inverted_period(
    actor: User,
    process: OffboardingProcess,
) -> None:
    response = logged_client(actor).get(
        REPORTS_URL,
        data={"start": "2026-07-31", "end": "2026-07-01"},
    )

    assert response.status_code == 400


def export(user: User, dataset: str, **params: Any) -> Any:
    return logged_client(user).get(f"/api/v1/reporting/exports/{dataset}.csv", data=params)


def linhas_csv(response: Any) -> list[list[str]]:
    conteudo = response.content.decode("utf-8-sig")
    return [linha.split(";") for linha in conteudo.strip().splitlines()]


def test_export_of_processes_carries_the_counts_and_records_the_act(
    actor: User,
    process: OffboardingProcess,
) -> None:
    task = analysis_task(actor, process)
    create_pending(actor, task)

    response = export(actor, "processos")

    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/csv")
    assert "attachment" in response["Content-Disposition"]
    # Sem o BOM o Excel pt-BR abre a acentuação quebrada.
    assert response.content.startswith(b"\xef\xbb\xbf")
    cabecalho, linha = linhas_csv(response)
    assert cabecalho[0] == "Referência"
    assert linha[0] == str(process.uuid)[:8]
    assert linha[2] == "Iniciado"
    assert linha[cabecalho.index("Tarefas")] == "1"
    assert linha[cabecalho.index("Tarefas em aberto")] == "1"
    assert linha[cabecalho.index("Pendências")] == "1"

    trilha = ReportExport.objects.get()
    assert trilha.dataset == ExportDataset.PROCESSES
    assert trilha.actor == actor
    assert trilha.row_count == 1


def test_export_of_pendings_carries_the_amount_and_never_the_opinion(
    actor: User,
    process: OffboardingProcess,
) -> None:
    """Número, estado e autor vão; texto de juízo e CPF não (`SECURITY.md` §5)."""

    task = analysis_task(actor, process)
    enable_amounts(task)
    register_amount(actor, create_value_pending(actor, task))

    response = export(actor, "pendencias")

    cabecalho, linha = linhas_csv(response)
    assert linha[cabecalho.index("Categoria")] == "Valor"
    assert linha[cabecalho.index("Bloqueio")] == "Bloqueante até decisão"
    assert linha[cabecalho.index("Moeda")] == "BRL"
    # Decimal com vírgula: o arquivo é lido em planilha pt-BR.
    assert linha[cabecalho.index("Informado")] == "1250,00"
    assert linha[cabecalho.index("Segregação rompida")] == "Não"
    assert "Justificativa" not in cabecalho
    assert "CPF" not in cabecalho
    conteudo = response.content.decode("utf-8-sig")
    assert "Valor de mercado" not in conteudo


def test_export_of_tasks_measures_the_hours_until_completion(
    actor: User,
    process: OffboardingProcess,
) -> None:
    task = started_task(actor, process)
    start_task(actor, task)
    task.refresh_from_db()
    complete_task(actor, task)
    task.refresh_from_db()
    concluida = task.completed_at
    assert concluida is not None
    task.started_at = concluida - timedelta(hours=3)
    task.save(update_fields=("started_at",))

    response = export(actor, "tarefas")

    cabecalho, linha = linhas_csv(response)
    assert linha[cabecalho.index("Situação")] == "Concluída"
    assert linha[cabecalho.index("Horas até concluir")] == "3,00"
    assert linha[cabecalho.index("Concluída por")] == actor.username


def test_export_refuses_a_cut_larger_than_the_file_limit(
    actor: User,
    process: OffboardingProcess,
) -> None:
    """Arquivo truncado em silêncio seria pior: quem confere somaria o que não
    é o total e não teria como saber."""

    started_task(actor, process)

    with mock.patch("apps.reporting.exports.EXPORT_ROWS", 0):
        response = export(actor, "processos")

    assert response.status_code == 400
    assert response.json()["code"] == "export_too_large"
    # Recusado não é acesso: nada foi gerado, nada entra na trilha.
    assert not ReportExport.objects.exists()


def test_export_refuses_unknown_dataset_and_actor_without_dp(
    actor: User,
    process: OffboardingProcess,
) -> None:
    task = started_task(actor, process)
    responsible = User.objects.create_user(
        username="setor.exporta",
        email="setor.exporta@example.invalid",
        password=PASSWORD,
    )
    SectorResponsible.objects.create(
        sector_id=task.sector_id,
        user=responsible,
        valid_from=timezone.now() - timedelta(hours=1),
        assigned_by=actor,
        updated_by=actor,
    )

    assert export(actor, "inexistente").status_code == 404
    assert export(responsible, "processos").status_code == 403
    assert not ReportExport.objects.exists()


def test_the_export_trail_is_append_only(
    actor: User,
    process: OffboardingProcess,
) -> None:
    started_task(actor, process)
    export(actor, "processos")
    trilha = ReportExport.objects.get()

    with pytest.raises(ValidationError):
        trilha.row_count = 99
        trilha.save(update_fields=("row_count",))
    with pytest.raises(ValidationError):
        trilha.delete()
    with pytest.raises(ValidationError):
        ReportExport.objects.update(row_count=99)


def test_the_process_export_never_asks_oracle_to_group_by_a_lob(
    actor: User,
    process: OffboardingProcess,
) -> None:
    """`annotate(Count(...))` sobre o processo levaria `REASON`/`NOTES` ao
    `GROUP BY`, e o Oracle recusa agrupar por LOB (ORA-00932). As contagens
    saem de consultas próprias e se juntam em Python."""

    started_task(actor, process)
    client = logged_client(actor)

    with CaptureQueriesContext(connection) as captured:
        assert client.get("/api/v1/reporting/exports/processos.csv").status_code == 200

    agrupadas = [
        query["sql"].upper()
        for query in captured.captured_queries
        if "GROUP BY" in query["sql"].upper()
    ]
    assert not [sql for sql in agrupadas if "REASON" in sql or "NOTES" in sql]
