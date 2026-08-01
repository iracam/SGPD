import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { provideRouter } from '@angular/router';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import { Relatorios } from './models/relatorios.models';
import { RelatoriosPage } from './relatorios';

const PROCESSO = '9cbed216-0000-0000-0000-000000000000';

function relatorios(overrides: Partial<Relatorios> = {}): Relatorios {
  return {
    period: { start: '2026-05-02', end: '2026-07-31' },
    process_cycle_time: { processes: 4, average_days: 12.5, median_days: 9.0 },
    sector_cycle_time: [
      { key: '7', label: 'Almoxarifado BSA', total: 3, average_hours: 26.5 },
    ],
    pending_by_category: [
      { key: 'EQUIPAMENTO', label: 'Equipamento', total: 5, detail: 2 },
      { key: 'VALOR', label: 'Valor', total: 2, detail: 1 },
    ],
    processes_by_company: [{ key: '1', label: 'Empresa 1', total: 6, detail: 0 }],
    overdue_processes: {
      total: 1,
      results: [
        {
          process_uuid: PROCESSO,
          process_ref: '9cbed216',
          employee_name: 'Colaborador de Homologação',
          company_code: 1,
          branch_code: 2,
          due_date: '2026-07-20',
          days_overdue: 11,
          open_tasks: 3,
        },
      ],
    },
    sector_delays: [{ key: '7', label: 'Almoxarifado BSA', total: 3, average_hours: 52.0 }],
    amounts: [{ currency: 'BRL', informed: '1250.00', approved: '980.00', undecided: 1 }],
    released_processes: {
      total: 2,
      results: [{ key: '2026-07-01', label: 'jul/2026', total: 2, detail: 0 }],
    },
    ...overrides,
  };
}

describe('RelatoriosPage', () => {
  let fixture: ComponentFixture<RelatoriosPage>;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideAnimationsAsync(),
        provideRouter([]),
      ],
    });
    fixture = TestBed.createComponent(RelatoriosPage);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  function carregar(dados: Partial<Relatorios> = {}): void {
    httpMock.expectOne('/api/v1/reporting/reports/').flush(relatorios(dados));
    fixture.detectChanges();
  }

  it('mostra tempo médio, atraso e valores do período', () => {
    carregar();

    const texto = fixture.nativeElement.textContent as string;
    expect(texto).toContain('12,5 dias');
    expect(texto).toContain('26,5 h');
    expect(texto).toContain('Equipamento');
    expect(texto).toContain('2 bloqueando');
    expect(texto).toContain('BRL 1.250,00');
    expect(texto).toContain('BRL 980,00');
    expect(texto).toContain('jul/2026');
    // Enum cru não chega ao usuário (ADR-047).
    expect(texto).not.toContain('EQUIPAMENTO');
  });

  it('diz que o atraso é fotografia de agora, não recorte do período', () => {
    carregar();

    expect(fixture.nativeElement.textContent).toContain('Fotografia deste instante');
    const link = fixture.nativeElement.querySelector(
      `a[href="/fe/processos/${PROCESSO}/encerramento"]`,
    ) as HTMLAnchorElement | null;
    expect(link?.textContent).toContain('Colaborador de Homologação');
  });

  it('consulta de novo com o período informado', () => {
    carregar();

    const componente = fixture.componentInstance as unknown as {
      inicio: string;
      fim: string;
      consultar(): void;
    };
    expect(componente.inicio).toBe('2026-05-02');
    componente.inicio = '2026-01-01';
    componente.fim = '2026-03-31';
    componente.consultar();

    const request = httpMock.expectOne(
      (candidate) => candidate.url === '/api/v1/reporting/reports/',
    );
    expect(request.request.params.get('start')).toBe('2026-01-01');
    expect(request.request.params.get('end')).toBe('2026-03-31');
    request.flush(relatorios({ period: { start: '2026-01-01', end: '2026-03-31' } }));
  });

  it('exporta cada conjunto no período em vigor', () => {
    carregar();

    const links = Array.from(
      fixture.nativeElement.querySelectorAll('a.acao') as NodeListOf<HTMLAnchorElement>,
    ).map((element) => element.getAttribute('href'));
    expect(links).toEqual([
      '/api/v1/reporting/exports/processos.csv?start=2026-05-02&end=2026-07-31',
      '/api/v1/reporting/exports/tarefas.csv?start=2026-05-02&end=2026-07-31',
      '/api/v1/reporting/exports/pendencias.csv?start=2026-05-02&end=2026-07-31',
    ]);
    expect(fixture.nativeElement.textContent).toContain('não leva CPF');
  });

  it('informa período sem fato em vez de mostrar tabela vazia', () => {
    carregar({
      process_cycle_time: { processes: 0, average_days: null, median_days: null },
      sector_cycle_time: [],
      pending_by_category: [],
      processes_by_company: [],
      amounts: [],
      released_processes: { total: 0, results: [] },
    });

    const texto = fixture.nativeElement.textContent as string;
    expect(texto).toContain('Nenhuma tarefa concluída no período');
    expect(texto).toContain('Nenhuma pretensão informada no período');
    // O atraso continua visível: ele não depende do período.
    expect(texto).toContain('Colaborador de Homologação');
  });
});
