import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import { TarefaSetor } from './models/tarefas.models';
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
      },
    ],
    version: status === 'PENDENTE' ? 1 : status === 'EM_ANALISE' ? 2 : 3,
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

  function carregar(row: TarefaSetor): void {
    httpMock.expectOne('/api/v1/tasks/').flush({
      offset: 0,
      limit: 50,
      results: [row],
    });
    fixture.detectChanges();
  }

  it('lista somente as tarefas devolvidas pelo servidor', () => {
    carregar(tarefa());

    expect(component.tarefas()).toHaveLength(1);
    expect(fixture.nativeElement.textContent).toContain('Tecnologia da Informação');
    expect(fixture.nativeElement.textContent).toContain('Pessoa de Teste');
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
  });
});
