import { provideHttpClient } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { ActivatedRoute, provideRouter } from '@angular/router';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import { ConsolidacaoValores } from './models/processo-valores.models';
import { ProcessoValoresPage } from './processo-valores';

const UUID = '3ca25d06-ca5d-4a49-a9df-d42d74a1d6b2';

function consolidacao(overrides: Partial<ConsolidacaoValores> = {}): ConsolidacaoValores {
  return {
    process: {
      uuid: UUID,
      status: 'INICIADO',
      company_code: 1,
      branch_code: 2,
      employee_name: 'Pessoa de Teste',
      employee_registration: 123,
    },
    totals: [
      {
        currency: 'BRL',
        informed: '1550.00',
        assessed: '1100.00',
        contested: '0.00',
        approved: '980.00',
        processed: '0.00',
      },
    ],
    undecided_count: 1,
    pending_items: [
      {
        uuid: 'f036642b-6e39-43c3-851a-d9f4d7b17ad3',
        title: 'Notebook não devolvido',
        status: 'APROVADA_COBRANCA',
        blocking_level: 'BLOQUEANTE_ATE_DECISAO',
        task_id: 11,
        sector: { id: 7, code: '7', name: 'Tecnologia da Informação' },
        amount: {
          amount_informed: '1250.00',
          amount_assessed: '1100.00',
          amount_contested: null,
          amount_approved: '980.00',
          amount_processed: null,
          currency: 'BRL',
          justification: 'Valor de mercado do equipamento.',
          informed_by: { id: 1, username: 'responsavel' },
          informed_at: '2026-07-30T10:00:00-03:00',
          approved_by: { id: 2, username: 'dp' },
          approved_at: '2026-07-31T10:00:00-03:00',
          version: 3,
          decisions: [],
        },
      },
    ],
    segregation_overrides: [],
    ...overrides,
  };
}

describe('ProcessoValoresPage', () => {
  let fixture: ComponentFixture<ProcessoValoresPage>;
  let httpMock: HttpTestingController;

  beforeEach(() => {
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
      ],
    });
    fixture = TestBed.createComponent(ProcessoValoresPage);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  function carregar(dados: ConsolidacaoValores): void {
    httpMock.expectOne(`/api/v1/processes/${UUID}/amounts/`).flush(dados);
    fixture.detectChanges();
  }

  it('soma por moeda e mostra a pretensão com o setor de origem', () => {
    carregar(consolidacao());

    const texto = fixture.nativeElement.textContent as string;
    expect(texto).toContain('BRL 1.550,00');
    expect(texto).toContain('BRL 980,00');
    expect(texto).toContain('Notebook não devolvido');
    expect(texto).toContain('Tecnologia da Informação');
    expect(texto).toContain('Aprovada para cobrança');
    expect(texto).not.toContain('Segregação rompida');
  });

  it('separa as decisões tomadas por quem informou o valor', () => {
    carregar(
      consolidacao({
        segregation_overrides: [
          {
            id: 1,
            pending_uuid: 'f036642b-6e39-43c3-851a-d9f4d7b17ad3',
            pending_title: 'Notebook não devolvido',
            decision: 'ABONADA',
            opinion: 'Abonado pela própria autoridade global.',
            decided_by: { id: 9, username: 'super' },
            decided_at: '2026-07-31T11:00:00-03:00',
          },
        ],
      }),
    );

    const texto = fixture.nativeElement.textContent as string;
    expect(texto).toContain('Segregação rompida');
    expect(texto).toContain('Abonada');
    expect(texto).toContain('super');
  });

  it('informa quando o processo não tem pretensão registrada', () => {
    carregar(
      consolidacao({ totals: [], pending_items: [], undecided_count: 0 }),
    );

    expect(fixture.nativeElement.textContent).toContain(
      'Nenhuma pretensão de cobrança registrada',
    );
  });
});
