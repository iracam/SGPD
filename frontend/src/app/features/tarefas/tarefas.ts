import { DatePipe } from '@angular/common';
import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ButtonModule } from 'primeng/button';
import { MessageModule } from 'primeng/message';
import { TagModule } from 'primeng/tag';
import { finalize } from 'rxjs';

import { errorMessage } from '../../core/api/api-error';
import { ItemChecklist, TarefaSetor } from './models/tarefas.models';
import { TarefasService } from './tarefas.service';

interface ProcessoComTarefas {
  uuid: string;
  companyCode: number;
  branchCode: number;
  employeeName: string;
  employeeRegistration: number;
  dueDate: string;
  tarefas: TarefaSetor[];
}

function agruparPorProcesso(
  tarefas: TarefaSetor[],
  concluido: boolean,
): ProcessoComTarefas[] {
  const ordenadas = [...tarefas].sort((left, right) => {
    const leftDate = concluido ? left.completed_at : left.due_at;
    const rightDate = concluido ? right.completed_at : right.due_at;
    const difference = new Date(rightDate ?? 0).getTime() - new Date(leftDate ?? 0).getTime();
    return concluido ? difference : -difference;
  });
  const processos = new Map<string, ProcessoComTarefas>();
  for (const tarefa of ordenadas) {
    const current = processos.get(tarefa.process.uuid);
    if (current) {
      current.tarefas.push(tarefa);
      continue;
    }
    processos.set(tarefa.process.uuid, {
      uuid: tarefa.process.uuid,
      companyCode: tarefa.process.company_code,
      branchCode: tarefa.process.branch_code,
      employeeName: tarefa.process.employee_name,
      employeeRegistration: tarefa.process.employee_registration,
      dueDate: tarefa.process.due_date,
      tarefas: [tarefa],
    });
  }
  return [...processos.values()];
}

@Component({
  selector: 'app-tarefas-page',
  imports: [DatePipe, ButtonModule, MessageModule, TagModule],
  templateUrl: './tarefas.html',
  styleUrl: './tarefas.scss',
})
export class TarefasPage {
  private readonly service = inject(TarefasService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly idempotencyKeys = new Map<string, string>();

  readonly tarefas = signal<TarefaSetor[]>([]);
  readonly carregando = signal(true);
  readonly tarefaEmMutacao = signal<number | null>(null);
  readonly erro = signal('');
  readonly aviso = signal('');
  readonly respostas = signal<Record<number, unknown>>({});
  readonly observacoes = signal<Record<number, string>>({});
  readonly grupos = computed(() => {
    const tarefas = this.tarefas();
    return [
      {
        key: 'ativas',
        title: 'Ativas (a concluir)',
        description: 'Pendentes e em análise.',
        icon: 'pi pi-clock',
        emptyTitle: 'Nenhuma tarefa ativa',
        emptyText: 'Não há tarefas pendentes ou em análise para seus vínculos vigentes.',
        processos: agruparPorProcesso(
          tarefas.filter((tarefa) => tarefa.status !== 'CONCLUIDA'),
          false,
        ),
      },
      {
        key: 'concluidas',
        title: 'Concluídas',
        description: 'Da conclusão mais nova para a mais antiga.',
        icon: 'pi pi-check-circle',
        emptyTitle: 'Nenhuma tarefa concluída',
        emptyText: 'As tarefas concluídas aparecerão aqui, com as mais novas no topo.',
        processos: agruparPorProcesso(
          tarefas.filter((tarefa) => tarefa.status === 'CONCLUIDA'),
          true,
        ),
      },
    ];
  });

  constructor() {
    this.carregar();
  }

  protected iniciar(tarefa: TarefaSetor): void {
    if (this.tarefaEmMutacao() !== null || tarefa.status !== 'PENDENTE') {
      return;
    }
    this.tarefaEmMutacao.set(tarefa.id);
    this.limparMensagens();
    this.service
      .iniciar(tarefa.id, tarefa.version, this.chave(`start:${tarefa.id}`))
      .pipe(
        finalize(() => this.tarefaEmMutacao.set(null)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (atualizada) => {
          this.substituir(atualizada);
          this.aviso.set(
            atualizada.idempotency_replayed
              ? 'O início anterior foi recuperado sem duplicação.'
              : 'Tarefa colocada em análise.',
          );
        },
        error: (error) =>
          this.erro.set(errorMessage(error, 'Não foi possível iniciar a tarefa.')),
      });
  }

  protected concluir(tarefa: TarefaSetor): void {
    if (this.tarefaEmMutacao() !== null || tarefa.status !== 'EM_ANALISE') {
      return;
    }
    const respostas = this.respostas();
    this.tarefaEmMutacao.set(tarefa.id);
    this.limparMensagens();
    this.service
      .concluir(
        tarefa.id,
        {
          expected_version: tarefa.version,
          answers: tarefa.checklist_items
            .filter((item) => Object.hasOwn(respostas, item.id))
            .map((item) => ({ item_id: item.id, value: respostas[item.id] })),
          notes: this.observacoes()[tarefa.id] ?? '',
        },
        this.chave(`complete:${tarefa.id}`),
      )
      .pipe(
        finalize(() => this.tarefaEmMutacao.set(null)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (atualizada) => {
          this.substituir(atualizada);
          this.aviso.set(
            atualizada.idempotency_replayed
              ? 'A conclusão anterior foi recuperada sem duplicação.'
              : 'Tarefa concluída e auditada.',
          );
        },
        error: (error) =>
          this.erro.set(errorMessage(error, 'Não foi possível concluir a tarefa.')),
      });
  }

  protected atualizarResposta(item: ItemChecklist, event: Event): void {
    const target = event.target;
    let value: unknown;
    if (target instanceof HTMLSelectElement && target.multiple) {
      value = Array.from(target.selectedOptions).map((option) => option.value);
    } else if (target instanceof HTMLInputElement && item.response_type === 'CONFIRMATION') {
      value = target.checked ? true : undefined;
    } else if (target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement) {
      value = target.value;
    } else if (target instanceof HTMLSelectElement) {
      value = target.value;
    }
    if (value === '') {
      value = undefined;
    } else if (item.response_type === 'BOOLEAN') {
      value = value === 'true';
    } else if (item.response_type === 'NUMBER' && typeof value === 'string') {
      value = Number(value);
    }
    this.respostas.update((current) => {
      const next = { ...current };
      if (value === undefined) {
        delete next[item.id];
      } else {
        next[item.id] = value;
      }
      return next;
    });
  }

  protected atualizarObservacao(taskId: number, event: Event): void {
    const value = event.target instanceof HTMLTextAreaElement ? event.target.value : '';
    this.observacoes.update((current) => ({ ...current, [taskId]: value }));
  }

  protected severidade(tarefa: TarefaSetor): 'warn' | 'info' | 'success' {
    if (tarefa.status === 'CONCLUIDA') {
      return 'success';
    }
    return tarefa.status === 'EM_ANALISE' ? 'info' : 'warn';
  }

  private carregar(): void {
    this.carregando.set(true);
    this.limparMensagens();
    this.service
      .listar()
      .pipe(
        finalize(() => this.carregando.set(false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (result) => this.tarefas.set(result.results),
        error: (error) =>
          this.erro.set(errorMessage(error, 'Não foi possível carregar as tarefas.')),
      });
  }

  private substituir(atualizada: TarefaSetor): void {
    this.tarefas.update((tarefas) =>
      tarefas.map((tarefa) => (tarefa.id === atualizada.id ? atualizada : tarefa)),
    );
  }

  private limparMensagens(): void {
    this.erro.set('');
    this.aviso.set('');
  }

  private chave(action: string): string {
    const existing = this.idempotencyKeys.get(action);
    if (existing) {
      return existing;
    }
    const generated =
      typeof crypto !== 'undefined' && 'randomUUID' in crypto
        ? crypto.randomUUID()
        : `${action}-${Date.now()}`;
    this.idempotencyKeys.set(action, generated);
    return generated;
  }
}
