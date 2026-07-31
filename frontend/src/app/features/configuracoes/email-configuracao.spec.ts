import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { provideRouter } from '@angular/router';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import { apiConfig } from '../../core/config/api.config';
import { EmailConfiguracaoPage } from './email-configuracao';
import { EmailConfiguration } from './models/configuracoes.models';

function configuracao(overrides: Partial<EmailConfiguration> = {}): EmailConfiguration {
  return {
    source: 'database',
    version: 3,
    enabled: true,
    host: 'smtp.office365.com',
    port: 587,
    use_tls: true,
    username: 'noreply@empresa.invalid',
    password_configured: true,
    timeout_seconds: 10,
    default_from_email: 'noreply@empresa.invalid',
    base_url: 'https://sgpd.empresa.invalid',
    max_attempts: 5,
    batch_size: 50,
    stale_minutes: 15,
    task_due_soon_hours: 48,
    task_due_imminent_hours: 24,
    task_critical_hours: 48,
    process_due_soon_hours: 72,
    validation: { valid: true, errors: [], warnings: [] },
    delivery_test: {
      tested_at: '2026-07-31T10:00:00-03:00',
      success: true,
      recipient: 'super@empresa.invalid',
      error: null,
      tested_by: 'super',
    },
    updated_at: '2026-07-31T09:00:00-03:00',
    updated_by: 'super',
    ...overrides,
  };
}

describe('EmailConfiguracaoPage', () => {
  let fixture: ComponentFixture<EmailConfiguracaoPage>;
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
    fixture = TestBed.createComponent(EmailConfiguracaoPage);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  function carregar(dados: EmailConfiguration = configuracao()): void {
    httpMock.expectOne(apiConfig.routes.settingsEmail).flush(dados);
    fixture.detectChanges();
  }

  it('mostra a configuração vigente e a origem efetiva', () => {
    carregar();

    const texto = fixture.nativeElement.textContent as string;
    expect(texto).toContain('Schema SGPD');
    expect(texto).toContain('noreply@empresa.invalid');
    expect(texto).toContain('Habilitado');
    expect(texto).toContain('Entregue');
  });

  it('envia a versão e omite a senha quando o campo fica vazio', () => {
    carregar();

    const form = fixture.nativeElement.querySelector('form') as HTMLFormElement;
    form.dispatchEvent(new Event('submit'));

    const request = httpMock.expectOne(apiConfig.routes.settingsEmail);
    expect(request.request.method).toBe('PUT');
    expect(request.request.body.version).toBe(3);
    expect(request.request.body.password).toBe('');
    expect(request.request.body.host).toBe('smtp.office365.com');
    request.flush(configuracao({ version: 4 }));
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain('salva e auditada');
  });

  it('destaca o aviso de URL base sem bloquear o salvamento', () => {
    carregar(
      configuracao({
        base_url: '',
        validation: {
          valid: true,
          errors: [],
          warnings: ['Sem URL base os links das mensagens saem relativos.'],
        },
      }),
    );

    expect(fixture.nativeElement.textContent).toContain('Funciona, mas vale conferir');
    expect(fixture.nativeElement.textContent).toContain('links das mensagens saem relativos');
  });

  it('pede a prova de envio sem corpo e recarrega a configuração', () => {
    carregar();

    const botao = Array.from(
      fixture.nativeElement.querySelectorAll('button') as NodeListOf<HTMLButtonElement>,
    ).find((element) => element.textContent?.includes('mensagem de prova'));
    botao?.click();

    const request = httpMock.expectOne(apiConfig.routes.settingsEmailDeliveryTest);
    expect(request.request.method).toBe('POST');
    request.flush({
      success: true,
      recipient: 'super@empresa.invalid',
      tested_at: '2026-07-31T12:00:00-03:00',
    });
    httpMock.expectOne(apiConfig.routes.settingsEmail).flush(configuracao());
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain('prova enviada para super@empresa.invalid');
  });
});
