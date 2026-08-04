import { provideHttpClient } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { ActivatedRoute, provideRouter } from '@angular/router';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import { AuthService } from '../../core/auth/auth.service';
import { ConferenciaEncerramento } from './models/processo-encerramento.models';
import { ProcessoEncerramentoPage } from './processo-encerramento';

const UUID = '0f0d1f8e-9f2a-4a3a-9c1a-6f6c0b0b1111';

let superusuario = false;

function conferencia(
  overrides: Partial<ConferenciaEncerramento> = {},
): ConferenciaEncerramento {
  return {
    process: {
      uuid: UUID,
      status: 'INICIADO',
      company_code: 1,
      branch_code: 2,
      employee_registration: 321,
      planned_termination_date: '2026-08-15',
      due_date: '2026-08-14',
      version: 4,
      formal: {
        released_at: null,
        released_by: null,
        release_notes: '',
        release_override_reason: '',
        termination_reference: '',
        termination_processed_on: null,
        processing_registered_at: null,
        processing_registered_by: null,
        processing_notes: '',
        closed_at: null,
        closed_by: null,
        closing_notes: '',
        closing_override_reason: '',
        cancelled_at: null,
        cancelled_by: null,
        cancellation_reason: '',
      },
      employee_snapshot: {
        employee_name: 'Pessoa de Teste',
        registration: 321,
        branch_legal_name: 'Filial Central',
      },
    },
    readiness: {
      situation: 'PRONTO_PARA_ANALISE_DP',
      is_ready: true,
      blockers: [],
      warnings: [],
      task_count: 1,
      required_task_count: 1,
      completed_task_count: 1,
      open_task_count: 0,
      blocking_pending_count: 0,
      open_pending_count: 0,
      undecided_amount_count: 0,
    },
    closing_blockers: [],
    can_override_blockers: false,
    tasks: [
      {
        id: 11,
        status: 'CONCLUIDA',
        sector: { id: 7, code: 'TI', name: 'Tecnologia da Informação' },
        due_at: '2026-08-10T18:00:00-03:00',
        completed_at: '2026-08-09T10:00:00-03:00',
      },
    ],
    ...overrides,
  };
}

describe('ProcessoEncerramentoPage', () => {
  let fixture: ComponentFixture<ProcessoEncerramentoPage>;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    superusuario = false;
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideAnimationsAsync(),
        provideRouter([]),
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { paramMap: { get: () => UUID } } },
        },
        {
          provide: AuthService,
          useValue: { currentUser: () => ({ is_superuser: superusuario }) },
        },
      ],
    });
    fixture = TestBed.createComponent(ProcessoEncerramentoPage);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  function carregar(dados: ConferenciaEncerramento): void {
    httpMock.expectOne(`/api/v1/processes/${UUID}/readiness/`).flush(dados);
    fixture.detectChanges();
  }

  function preencher(seletor: string, valor: string): void {
    const campo = fixture.nativeElement.querySelector(seletor) as HTMLTextAreaElement;
    campo.value = valor;
    campo.dispatchEvent(new Event('input'));
    fixture.detectChanges();
  }

  function preencherIndice(indice: number, valor: string): void {
    const campo = fixture.nativeElement.querySelectorAll('textarea')[
      indice
    ] as HTMLTextAreaElement;
    campo.value = valor;
    campo.dispatchEvent(new Event('input'));
    fixture.detectChanges();
  }

  it('separa o estado formal da situação calculada e lista os impedimentos', () => {
    carregar(
      conferencia({
        readiness: {
          ...conferencia().readiness,
          situation: 'AGUARDANDO_DECISAO',
          is_ready: false,
          blockers: ['A pretensão de Financeiro em Multa ainda não foi decidida.'],
          warnings: ['A pendência Crachá de Portaria continua aberta.'],
        },
      }),
    );

    const texto = fixture.nativeElement.textContent as string;
    expect(texto).toContain('Iniciado');
    expect(texto).toContain('Aguardando decisão');
    expect(texto).toContain('ainda não foi decidida');
    expect(texto).toContain('continua aberta');
    const liberar = fixture.nativeElement.querySelector(
      'p-button[label="Liberar para rescisão"] button',
    ) as HTMLButtonElement;
    expect(liberar.disabled).toBe(true);
  });

  it('não lista impedimento da liberação em processo cancelado', () => {
    // No terminal a liberação não é mais alcançável: repetir o que a impedia é
    // ruído sobre um processo em que nada há a fazer.
    carregar(
      conferencia({
        process: {
          ...conferencia().process,
          status: 'CANCELADO',
          formal: {
            ...conferencia().process.formal,
            cancelled_at: '2026-07-31T22:42:51Z',
            cancelled_by: { id: 1, username: 'macari' },
            cancellation_reason: 'Abertura indevida.',
          },
        },
        readiness: {
          ...conferencia().readiness,
          situation: 'CANCELADO',
          is_ready: false,
          blockers: ['O processo não possui tarefas de setor.'],
        },
      }),
    );

    const texto = fixture.nativeElement.textContent as string;
    expect(texto).toContain('Cancelado');
    expect(texto).toContain('Abertura indevida.');
    expect(texto).not.toContain('O processo não possui tarefas de setor.');
    expect(texto).not.toContain('Nenhum impedimento para a liberação.');
    // As contagens continuam: são conferência, não impedimento.
    expect(fixture.nativeElement.querySelector('.contagens')).not.toBeNull();
  });

  it('libera com a versão esperada e chave de idempotência', () => {
    carregar(conferencia());
    preencher('textarea', 'Consolidado conferido.');

    (
      fixture.nativeElement.querySelector(
        'p-button[label="Liberar para rescisão"] button',
      ) as HTMLButtonElement
    ).click();

    const request = httpMock.expectOne(`/api/v1/processes/${UUID}/release/`);
    expect(request.request.body).toEqual({
      expected_version: 4,
      notes: 'Consolidado conferido.',
    });
    expect(request.request.headers.get('Idempotency-Key')).toBeTruthy();
    request.flush(
      conferencia({
        process: { ...conferencia().process, status: 'LIBERADO_PARA_RESCISAO' },
      }),
    );
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain(
      'Processo liberado para rescisão.',
    );
  });

  it('mostra o impedimento recalculado quando o servidor recusa a liberação', () => {
    carregar(conferencia());

    (
      fixture.nativeElement.querySelector(
        'p-button[label="Liberar para rescisão"] button',
      ) as HTMLButtonElement
    ).click();

    httpMock.expectOne(`/api/v1/processes/${UUID}/release/`).flush(
      {
        code: 'validation_error',
        message: 'Os dados enviados são inválidos.',
        details: { release: ['A tarefa obrigatória de Financeiro não foi concluída.'] },
      },
      { status: 400, statusText: 'Bad Request' },
    );
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain(
      'A tarefa obrigatória de Financeiro não foi concluída.',
    );
  });

  it('não oferece override da liberação sem can_override_blockers', () => {
    carregar(
      conferencia({
        readiness: {
          ...conferencia().readiness,
          is_ready: false,
          blockers: ['A tarefa obrigatória de Financeiro não foi concluída.'],
        },
        can_override_blockers: false,
      }),
    );

    expect(fixture.nativeElement.textContent).toContain(
      'A liberação fica indisponível enquanto houver impedimento acima.',
    );
    expect(
      fixture.nativeElement.querySelector(
        'p-button[label="Liberar com override dos impedimentos"]',
      ),
    ).toBeNull();
  });

  it('libera com override dos impedimentos quando autorizado', () => {
    carregar(
      conferencia({
        readiness: {
          ...conferencia().readiness,
          is_ready: false,
          blockers: ['A tarefa obrigatória de Financeiro não foi concluída.'],
        },
        can_override_blockers: true,
      }),
    );

    const override = () =>
      fixture.nativeElement.querySelector(
        'p-button[label="Liberar com override dos impedimentos"] button',
      ) as HTMLButtonElement;
    expect(override().disabled).toBe(true);

    preencherIndice(1, 'DP_GERENTE autoriza a liberação com pendência residual.');
    expect(override().disabled).toBe(false);
    override().click();

    const request = httpMock.expectOne(`/api/v1/processes/${UUID}/release/`);
    expect(request.request.body).toEqual({
      expected_version: 4,
      notes: '',
      override_reason: 'DP_GERENTE autoriza a liberação com pendência residual.',
    });
    request.flush(
      conferencia({
        process: { ...conferencia().process, status: 'LIBERADO_PARA_RESCISAO' },
      }),
    );
  });

  it('encerra com override dos impedimentos quando autorizado', () => {
    carregar(
      conferencia({
        process: { ...conferencia().process, status: 'RESCISAO_PROCESSADA' },
        readiness: { ...conferencia().readiness, situation: 'RESCISAO_PROCESSADA' },
        closing_blockers: ['A pendência Crachá de Portaria continua aberta.'],
        can_override_blockers: true,
      }),
    );

    const override = () =>
      fixture.nativeElement.querySelector(
        'p-button[label="Encerrar com override dos impedimentos"] button',
      ) as HTMLButtonElement;
    expect(override().disabled).toBe(true);

    preencherIndice(1, 'DP_GERENTE autoriza o encerramento com pendência residual.');
    expect(override().disabled).toBe(false);
    override().click();

    const request = httpMock.expectOne(`/api/v1/processes/${UUID}/close/`);
    expect(request.request.body).toEqual({
      expected_version: 4,
      notes: '',
      override_reason: 'DP_GERENTE autoriza o encerramento com pendência residual.',
    });
    request.flush(
      conferencia({
        process: { ...conferencia().process, status: 'ENCERRADO' },
      }),
    );
  });

  it('não oferece override do encerramento sem can_override_blockers', () => {
    carregar(
      conferencia({
        process: { ...conferencia().process, status: 'RESCISAO_PROCESSADA' },
        readiness: { ...conferencia().readiness, situation: 'RESCISAO_PROCESSADA' },
        closing_blockers: ['A pendência Crachá de Portaria continua aberta.'],
        can_override_blockers: false,
      }),
    );

    expect(fixture.nativeElement.textContent).toContain(
      'O encerramento fica indisponível enquanto houver impedimento acima.',
    );
    expect(
      fixture.nativeElement.querySelector(
        'p-button[label="Encerrar com override dos impedimentos"]',
      ),
    ).toBeNull();
  });

  it('exige motivo para cancelar e envia o texto informado', () => {
    carregar(conferencia());
    const cancelar = () =>
      fixture.nativeElement.querySelector(
        'p-button[label="Cancelar processo"] button',
      ) as HTMLButtonElement;
    expect(cancelar().disabled).toBe(true);

    const motivo = fixture.nativeElement.querySelectorAll(
      'textarea',
    )[1] as HTMLTextAreaElement;
    motivo.value = 'Colaborador desistiu do desligamento.';
    motivo.dispatchEvent(new Event('input'));
    fixture.detectChanges();

    cancelar().click();

    const request = httpMock.expectOne(`/api/v1/processes/${UUID}/cancel/`);
    expect(request.request.body).toEqual({
      expected_version: 4,
      reason: 'Colaborador desistiu do desligamento.',
    });
    request.flush(
      conferencia({
        process: {
          ...conferencia().process,
          status: 'CANCELADO',
          formal: {
            ...conferencia().process.formal,
            cancelled_at: '2026-08-01T10:00:00-03:00',
            cancelled_by: { id: 1, username: 'dp' },
            cancellation_reason: 'Colaborador desistiu do desligamento.',
          },
        },
        readiness: { ...conferencia().readiness, situation: 'CANCELADO' },
      }),
    );
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain('O cancelamento é terminal.');
  });

  it('não oferece a reabertura a quem não é SuperAdmin', () => {
    carregar(
      conferencia({
        process: { ...conferencia().process, status: 'ENCERRADO' },
        readiness: { ...conferencia().readiness, situation: 'ENCERRADO' },
      }),
    );

    expect(fixture.nativeElement.textContent).not.toContain('Reabrir processo');
  });

  it('reabre com motivo e as tarefas escolhidas quando é SuperAdmin', () => {
    superusuario = true;
    carregar(
      conferencia({
        process: { ...conferencia().process, status: 'ENCERRADO' },
        readiness: { ...conferencia().readiness, situation: 'ENCERRADO' },
      }),
    );

    preencher('textarea', 'Rescisão anulada pelo Jurídico.');
    const tarefa = fixture.nativeElement.querySelector(
      'input[type="checkbox"]',
    ) as HTMLInputElement;
    tarefa.click();
    fixture.detectChanges();

    (
      fixture.nativeElement.querySelector(
        'p-button[label="Reabrir processo"] button',
      ) as HTMLButtonElement
    ).click();

    const request = httpMock.expectOne(`/api/v1/processes/${UUID}/reopen/`);
    expect(request.request.body).toEqual({
      expected_version: 4,
      reason: 'Rescisão anulada pelo Jurídico.',
      task_ids: [11],
    });
    request.flush(conferencia());
  });
});
