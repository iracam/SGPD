import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { provideRouter } from '@angular/router';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import { FilaNotificacoes, Notificacao } from './models/notificacoes.models';
import { NotificacoesPage } from './notificacoes';

const UUID = '5f2b7a1e-6f4b-4d5e-9a0c-1b2c3d4e5f60';

function notificacao(overrides: Partial<Notificacao> = {}): Notificacao {
  return {
    uuid: UUID,
    event: 'TAREFA_VENCIDA',
    channel: 'EMAIL',
    status: 'FALHA',
    subject: 'Tarefa vencida no setor Tecnologia',
    body: 'A tarefa do setor Tecnologia venceu.',
    process_uuid: '9cbed216-0000-0000-0000-000000000000',
    process_ref: '9cbed216',
    task_id: 11,
    sector_name: 'Tecnologia da Informação',
    recipient: { id: 3, username: 'responsavel', email: 'responsavel@example.invalid' },
    attempts: 5,
    max_attempts: 5,
    next_attempt_at: '2026-07-31T10:00:00-03:00',
    sent_at: null,
    last_error: 'SMTPException: relay refused',
    created_at: '2026-07-31T09:00:00-03:00',
    version: 7,
    delivery_attempts: [
      {
        attempt_number: 1,
        started_at: '2026-07-31T09:01:00-03:00',
        finished_at: '2026-07-31T09:01:05-03:00',
        succeeded: false,
        error: 'SMTPException: relay refused',
      },
    ],
    ...overrides,
  };
}

describe('NotificacoesPage', () => {
  let fixture: ComponentFixture<NotificacoesPage>;
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
    fixture = TestBed.createComponent(NotificacoesPage);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  function carregar(fila: Partial<FilaNotificacoes> = {}): void {
    httpMock.expectOne('/api/v1/notifications/').flush({
      results: [notificacao()],
      summary: { FALHA: 1, ENVIADA: 4 },
      ...fila,
    });
    fixture.detectChanges();
  }

  it('mostra a fila com o resumo e o erro da última tentativa', () => {
    carregar();

    const texto = fixture.nativeElement.textContent as string;
    expect(texto).toContain('Tarefa vencida no setor Tecnologia');
    expect(texto).toContain('responsavel@example.invalid');
    expect(texto).toContain('SMTPException: relay refused');
    expect(texto).toContain('Falha');
    expect(texto).not.toContain('TAREFA_VENCIDA');
  });

  it('reprocessa a mensagem em falha com versão e chave de idempotência', () => {
    carregar();

    const botao = Array.from(
      fixture.nativeElement.querySelectorAll('button') as NodeListOf<HTMLButtonElement>,
    ).find((element) => element.textContent?.includes('Reprocessar'));
    expect(botao).toBeDefined();
    botao?.click();

    const request = httpMock.expectOne(`/api/v1/notifications/${UUID}/reprocess/`);
    expect(request.request.body).toEqual({ expected_version: 7 });
    expect(request.request.headers.get('Idempotency-Key')).toBeTruthy();
    request.flush(notificacao({ status: 'PENDENTE', attempts: 0, version: 8 }));

    // O reprocessamento recarrega a fila para mostrar a situação nova.
    httpMock.expectOne('/api/v1/notifications/').flush({ results: [], summary: {} });
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('devolvida à fila');
  });

  it('não oferece reprocessamento para mensagem já entregue', () => {
    carregar({
      results: [notificacao({ status: 'ENVIADA', sent_at: '2026-07-31T09:02:00-03:00' })],
    });

    const textos = Array.from(
      fixture.nativeElement.querySelectorAll('button') as NodeListOf<HTMLButtonElement>,
    ).map((element) => element.textContent ?? '');
    expect(textos.some((texto) => texto.includes('Reprocessar'))).toBe(false);
  });
});
