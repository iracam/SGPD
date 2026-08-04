import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { provideRouter } from '@angular/router';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { AuthService } from '../../core/auth/auth.service';
import { AuthContext } from '../../core/auth/models/auth.models';
import { Indicadores } from './models/painel.models';
import { PainelPage } from './painel';

const PROCESSO = '9cbed216-0000-0000-0000-000000000000';

function indicadores(overrides: Partial<Indicadores> = {}): Indicadores {
  return {
    generated_at: '2026-07-31T10:00:00-03:00',
    coordination: {
      open_processes: 3,
      completed_processes: 2,
      draft_processes: 1,
      cancelled_processes: 1,
      overdue_processes: 2,
      due_soon_processes: 1,
      open_pending_items: 4,
      blocking_pending_items: 2,
      amounts_awaiting_decision: 1,
      by_status: [
        { key: 'INICIADO', label: 'Iniciado', total: 3 },
        { key: 'CANCELADO', label: 'Cancelado', total: 1 },
      ],
      delayed_sectors: [{ key: '7', label: 'Almoxarifado BSA', total: 2 }],
      amount_totals: [{ currency: 'BRL', informed: '1250.00' }],
      critical_processes: [
        {
          process_uuid: PROCESSO,
          process_ref: '9cbed216',
          employee_name: 'Colaborador de Homologação',
          company_code: 1,
          branch_code: 2,
          due_date: '2026-07-20',
          overdue_tasks: 2,
        },
      ],
    },
    sector: null,
    ...overrides,
  };
}

describe('PainelPage', () => {
  let fixture: ComponentFixture<PainelPage>;
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
    fixture = TestBed.createComponent(PainelPage);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  function carregar(dados: Partial<Indicadores> = {}): void {
    httpMock.expectOne('/api/v1/reporting/dashboard/').flush(indicadores(dados));
    fixture.detectChanges();
  }

  it('mostra os indicadores de coordenação com rótulo legível', () => {
    carregar();

    const texto = fixture.nativeElement.textContent as string;
    expect(texto).toContain('Coordenação');
    expect(texto).toContain('Em aberto');
    expect(texto).toContain('Iniciado');
    expect(texto).toContain('Almoxarifado BSA');
    // Enum cru não chega ao usuário (ADR-047).
    expect(texto).not.toContain('INICIADO');
    expect(texto).toContain('BRL 1.250,00');
  });

  it('leva o processo crítico para a conferência do encerramento', () => {
    carregar();

    const link = fixture.nativeElement.querySelector(
      `a[href="/fe/processos/${PROCESSO}/encerramento"]`,
    ) as HTMLAnchorElement | null;
    expect(link?.textContent).toContain('Colaborador de Homologação');
  });

  it('omite o bloco de setor quando o backend não o devolve', () => {
    carregar();

    expect(fixture.nativeElement.textContent).not.toContain('Meus setores');
  });

  it('mostra o bloco de setor com as tarefas vencidas de quem responde por setor', () => {
    carregar({
      coordination: null,
      sector: {
        pending_tasks: 5,
        overdue_tasks: 2,
        due_soon_tasks: 1,
        by_company: [{ key: '1', label: 'Empresa 1', total: 5 }],
        by_branch: [{ key: '1:2', label: 'Filial Barueri', total: 5 }],
        critical_processes: [],
      },
    });

    const texto = fixture.nativeElement.textContent as string;
    expect(texto).toContain('Meus setores');
    expect(texto).toContain('Tarefas pendentes');
    expect(texto).toContain('Filial Barueri');
    expect(texto).not.toContain('Coordenação');
  });

  it('explica a ausência de indicadores em vez de mostrar painel vazio', () => {
    carregar({ coordination: null, sector: null });

    expect(fixture.nativeElement.textContent).toContain('ainda não coordena processos');
  });

  it('nomeia todo papel do catálogo em Seu acesso, sem enum cru', () => {
    // O rótulo cobria só `DP`: uma conta administrativa lia `USUARIOS_ADMIN`
    // na própria tela, contra a ADR-047.
    vi.spyOn(TestBed.inject(AuthService), 'currentContext').mockReturnValue({
      roles: ['DP_GERENTE', 'USUARIOS_ADMIN', 'RESPONSAVEL_SETOR'],
      scopes: { is_superuser: false, assignments: [] },
    } as unknown as AuthContext);
    carregar({ coordination: null, sector: null });

    const texto = fixture.nativeElement.textContent as string;
    expect(texto).toContain('Gerência do Departamento Pessoal');
    expect(texto).toContain('Administração de usuários');
    expect(texto).toContain('Responsável de setor');
    expect(texto).not.toContain('USUARIOS_ADMIN');
    expect(texto).not.toContain('DP_GERENTE');
  });

  it('oferece a ajuda da tela na seção do manual comum a toda conta', () => {
    carregar();

    const ajuda = fixture.nativeElement.querySelector(
      '.pagina-acoes a[target="_blank"]',
    ) as HTMLAnchorElement | null;
    expect(ajuda?.getAttribute('href')).toBe('/ajuda/primeiros-passos/#o-painel');
  });
});
