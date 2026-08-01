import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { provideRouter } from '@angular/router';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import { Operacao } from './models/operacao.models';
import { OperacaoPage } from './operacao';

function operacao(overrides: Partial<Operacao> = {}): Operacao {
  return {
    checked_at: '2026-07-31T10:00:00-03:00',
    queue: {
      counts: { PENDENTE: 4, ENVIADA: 16 },
      oldest_pending_at: '2026-07-31T08:00:00-03:00',
      last_sent_at: '2026-07-31T09:30:00-03:00',
      stale_minutes: 30,
      is_stalled: true,
      verdict:
        'Há mensagem pendente há mais de 30 minutos: o agendamento provavelmente parou.',
    },
    storage: { evidence_count: 3, evidence_bytes: 5 * 1024 * 1024 },
    retention: {
      closed_processes: 2,
      beyond_retention: 0,
      oldest_closed_at: '2026-07-31T09:00:00-03:00',
      retention_years: 5,
    },
    ...overrides,
  };
}

describe('OperacaoPage', () => {
  let fixture: ComponentFixture<OperacaoPage>;
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
    fixture = TestBed.createComponent(OperacaoPage);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  function carregar(dados: Partial<Operacao> = {}): void {
    httpMock.expectOne('/api/v1/reporting/operations/').flush(operacao(dados));
    fixture.detectChanges();
  }

  it('destaca a fila parada com o veredito do servidor', () => {
    carregar();

    const texto = fixture.nativeElement.textContent as string;
    expect(texto).toContain('agendamento provavelmente parou');
    expect(texto).toContain('Pendente');
    // Enum cru não chega ao usuário (ADR-047).
    expect(texto).not.toContain('PENDENTE');
  });

  it('mostra ocupação e retenção sem prometer expurgo automático', () => {
    carregar();

    const texto = fixture.nativeElement.textContent as string;
    expect(texto).toContain('5 MiB');
    expect(texto).toContain('Além de 5 anos');
    expect(texto).toContain('nenhuma rotina apaga arquivo');
  });

  it('não alarma quando a fila está apenas aguardando o próximo despacho', () => {
    carregar({
      queue: {
        counts: { PENDENTE: 1 },
        oldest_pending_at: '2026-07-31T09:59:00-03:00',
        last_sent_at: null,
        stale_minutes: 30,
        is_stalled: false,
        verdict: 'Fila com mensagem recente aguardando o próximo despacho.',
      },
    });

    const texto = fixture.nativeElement.textContent as string;
    expect(texto).toContain('aguardando o próximo despacho');
    expect(texto).toContain('Nunca');
    expect(texto).not.toContain('provavelmente parou');
  });
});
