import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import { Evidencia, Pendencia, TarefaSetor } from './models/tarefas.models';
import { TarefasPage } from './tarefas';

function tarefa(status: TarefaSetor['status'] = 'PENDENTE'): TarefaSetor {
  return {
    id: 11,
    status,
    sector: { id: 7, code: '7', name: 'Tecnologia da Informação' },
    template: { version_id: 20, code: '2', version_number: 1 },
    process: {
      uuid: '3ca25d06-ca5d-4a49-a9df-d42d74a1d6b2',
      company_code: 1,
      branch_code: 2,
      employee_name: 'Pessoa de Teste',
      employee_registration: 123,
      due_date: '2026-08-14',
    },
    is_required: true,
    blocks_process: true,
    sla_hours: 12,
    due_at: '2026-07-30T01:00:00-03:00',
    started_at: '2026-07-29T13:00:00-03:00',
    completed_at: status === 'CONCLUIDA' ? '2026-07-29T14:00:00-03:00' : null,
    notes: '',
    checklist_item_count: 1,
    checklist_items: [
      {
        id: 31,
        code: '31',
        question: 'Tudo certo?',
        response_type: 'BOOLEAN',
        is_required: true,
        blocks_process: false,
        requires_evidence: false,
        allows_pending: false,
        display_order: 1,
        config: {},
        response: status === 'CONCLUIDA' ? true : null,
        answered_at: status === 'CONCLUIDA' ? '2026-07-29T14:00:00-03:00' : null,
        evidences: [],
      },
    ],
    pending_items: [],
    evidences: [],
    version: status === 'PENDENTE' ? 1 : status === 'EM_ANALISE' ? 2 : 3,
  };
}

function pendencia(): Pendencia {
  return {
    uuid: 'f036642b-6e39-43c3-851a-d9f4d7b17ad3',
    process_uuid: tarefa().process.uuid,
    task_id: 11,
    checklist_item_id: 31,
    category: 'EQUIPAMENTO',
    title: 'Notebook pendente',
    description: 'Aguardar devolução.',
    status: 'ABERTA',
    blocking_level: 'BLOQUEANTE',
    identified_at: '2026-07-30T10:00:00-03:00',
    regularization_due_at: null,
    registered_by: { id: 1, username: 'responsavel' },
    version: 1,
    items: [],
    comments: [],
  };
}

function evidencia(): Evidencia {
  return {
    uuid: '0f964f68-f2ad-4096-a4d7-8c0fa6be228a',
    process_uuid: tarefa().process.uuid,
    task_id: 11,
    pending_uuid: null,
    checklist_item_id: 31,
    original_name: 'comprovante.png',
    mime_type: 'image/png',
    size_bytes: 1024,
    sha256: 'a'.repeat(64),
    uploaded_by: { id: 1, username: 'responsavel' },
    uploaded_at: '2026-07-30T10:00:00-03:00',
    classification: 'RESTRITA',
    download_url: '/api/v1/evidence/0f964f68-f2ad-4096-a4d7-8c0fa6be228a/download/',
  };
}

describe('TarefasPage', () => {
  let fixture: ComponentFixture<TarefasPage>;
  let component: TarefasPage;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideAnimationsAsync(),
      ],
    });
    fixture = TestBed.createComponent(TarefasPage);
    component = fixture.componentInstance;
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  function carregar(rows: TarefaSetor | TarefaSetor[]): void {
    httpMock.expectOne('/api/v1/tasks/').flush({
      offset: 0,
      limit: 50,
      results: Array.isArray(rows) ? rows : [rows],
    });
    fixture.detectChanges();
  }

  it('separa tarefas ativas e concluídas em dois cards', () => {
    carregar(tarefa());

    expect(component.tarefas()).toHaveLength(1);
    expect(component.grupos()[0].processos).toHaveLength(1);
    expect(component.grupos()[0].processos[0].tarefas).toHaveLength(1);
    expect(component.grupos()[1].processos).toHaveLength(0);
    expect(fixture.nativeElement.textContent).toContain('Ativas (a concluir)');
    expect(fixture.nativeElement.textContent).toContain('Concluídas');
    expect(fixture.nativeElement.textContent).toContain('Tecnologia da Informação');
    expect(fixture.nativeElement.textContent).toContain('Pessoa de Teste');
    const details = fixture.nativeElement.querySelector('details') as HTMLDetailsElement;
    expect(details.open).toBe(false);
    (details.querySelector('summary') as HTMLElement).click();
    expect(details.open).toBe(true);
  });

  it('ordena as concluídas da mais nova para a mais antiga', () => {
    const antiga = {
      ...tarefa('CONCLUIDA'),
      id: 10,
      completed_at: '2026-07-29T14:00:00-03:00',
      process: {
        ...tarefa('CONCLUIDA').process,
        uuid: 'processo-antigo',
        employee_name: 'Conclusão antiga',
      },
    };
    const nova = {
      ...tarefa('CONCLUIDA'),
      id: 12,
      completed_at: '2026-07-30T14:00:00-03:00',
      process: {
        ...tarefa('CONCLUIDA').process,
        uuid: 'processo-novo',
        employee_name: 'Conclusão nova',
      },
    };

    carregar([antiga, nova]);

    expect(
      component.grupos()[1].processos.map((processo) => processo.employeeName),
    ).toEqual(['Conclusão nova', 'Conclusão antiga']);
    const text = fixture.nativeElement.textContent as string;
    expect(text.indexOf('Conclusão nova')).toBeLessThan(text.indexOf('Conclusão antiga'));
  });

  it('inicia a análise com versão e chave idempotente', () => {
    const pendente = tarefa();
    carregar(pendente);

    (
      component as unknown as {
        iniciar(value: TarefaSetor): void;
      }
    ).iniciar(pendente);

    const request = httpMock.expectOne('/api/v1/tasks/11/start/');
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual({ expected_version: 1 });
    expect(request.request.headers.get('Idempotency-Key')).toBeTruthy();
    request.flush(tarefa('EM_ANALISE'));

    expect(component.tarefas()[0].status).toBe('EM_ANALISE');
  });

  it('envia as respostas tipadas e conclui a tarefa', () => {
    const emAnalise = tarefa('EM_ANALISE');
    carregar(emAnalise);
    const select = document.createElement('select');
    select.innerHTML = '<option value="true">Sim</option>';
    select.value = 'true';
    const actions = component as unknown as {
      atualizarResposta(item: TarefaSetor['checklist_items'][number], event: Event): void;
      concluir(value: TarefaSetor): void;
    };
    actions.atualizarResposta(
      emAnalise.checklist_items[0],
      { target: select } as unknown as Event,
    );
    actions.concluir(emAnalise);

    const request = httpMock.expectOne('/api/v1/tasks/11/complete/');
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual({
      expected_version: 2,
      answers: [{ item_id: 31, value: true }],
      notes: '',
    });
    expect(request.request.headers.get('Idempotency-Key')).toBeTruthy();
    request.flush(tarefa('CONCLUIDA'));

    expect(component.tarefas()[0].status).toBe('CONCLUIDA');
    expect(component.grupos()[0].processos).toHaveLength(0);
    expect(component.grupos()[1].processos).toHaveLength(1);
  });

  it('registra pendência estruturada com versão e idempotência', () => {
    const emAnalise = tarefa('EM_ANALISE');
    carregar(emAnalise);
    component.rascunhosPendencia.set({
      11: {
        title: 'Notebook pendente',
        description: 'Aguardar devolução.',
        category: 'EQUIPAMENTO',
        blocking_level: 'BLOQUEANTE',
        checklist_item_id: 31,
      },
    });

    (
      component as unknown as {
        criarPendencia(value: TarefaSetor): void;
      }
    ).criarPendencia(emAnalise);

    const request = httpMock.expectOne('/api/v1/pending-items/');
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual({
      task_id: 11,
      expected_task_version: 2,
      checklist_item_id: 31,
      category: 'EQUIPAMENTO',
      title: 'Notebook pendente',
      description: 'Aguardar devolução.',
      blocking_level: 'BLOQUEANTE',
      items: [],
    });
    expect(request.request.headers.get('Idempotency-Key')).toBeTruthy();
    request.flush(pendencia());

    expect(component.tarefas()[0].pending_items[0].title).toBe('Notebook pendente');
  });

  it('envia evidência privada vinculada ao item do checklist', () => {
    const emAnalise = tarefa('EM_ANALISE');
    emAnalise.checklist_items[0].requires_evidence = true;
    carregar(emAnalise);
    const file = new File(['conteúdo'], 'comprovante.png', { type: 'image/png' });
    const input = document.createElement('input');
    Object.defineProperty(input, 'files', { value: [file] });

    (
      component as unknown as {
        enviarEvidencia(
          task: TarefaSetor,
          event: Event,
          item: TarefaSetor['checklist_items'][number],
        ): void;
      }
    ).enviarEvidencia(
      emAnalise,
      { target: input } as unknown as Event,
      emAnalise.checklist_items[0],
    );

    const request = httpMock.expectOne('/api/v1/evidence/');
    expect(request.request.method).toBe('POST');
    const body = request.request.body as FormData;
    expect(body.get('task_id')).toBe('11');
    expect(body.get('expected_task_version')).toBe('2');
    expect(body.get('checklist_item_id')).toBe('31');
    expect(body.get('file')).toBe(file);
    request.flush(evidencia());

    expect(component.tarefas()[0].checklist_items[0].evidences).toHaveLength(1);
  });

  it('abre o comentário da pendência vazio, sem a string "undefined"', () => {
    const emAnalise = tarefa('EM_ANALISE');
    emAnalise.pending_items = [pendencia()];
    carregar(emAnalise);

    const comentario = [...fixture.nativeElement.querySelectorAll('label')]
      .find((label) => (label as HTMLLabelElement).textContent?.includes('Comentário'))
      ?.querySelector('textarea') as HTMLTextAreaElement | null;

    expect(comentario).toBeTruthy();
    expect(comentario?.value).toBe('');
  });
});
