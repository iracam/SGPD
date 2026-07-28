import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { provideRouter } from '@angular/router';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import { apiConfig } from '../../core/config/api.config';
import { LdapConfiguration } from './models/configuracoes.models';
import { LdapConfiguracaoPage } from './ldap-configuracao';

const CONFIGURATION: LdapConfiguration = {
  source: 'database',
  version: 3,
  enabled: true,
  authentication_enabled: false,
  server_address: 'ad.example.internal',
  use_tls: true,
  bind_dn: 'svc.sgpd@example.internal',
  bind_password_configured: true,
  user_search_base: 'OU=Usuarios,DC=example,DC=internal',
  group_search_base: 'OU=Grupos,DC=example,DC=internal',
  required_group_dn: 'CN=SGPD,OU=Grupos,DC=example,DC=internal',
  tls_require_certificate: true,
  connect_timeout_seconds: 5,
  receive_timeout_seconds: 10,
  page_size: 100,
  result_limit: 50,
  nested_group_search: true,
  local_superuser_fallback: true,
  user_extra_filter: '',
  secure_transport: true,
  validation: { valid: true, errors: [] },
  certificate: {
    configured: true,
    source: 'database',
    original_name: 'corporate-ca.pem',
    sha256: 'a'.repeat(64),
    subject: 'CN=Corporate CA',
    issuer: 'CN=Corporate CA',
    not_before: '2026-01-01T00:00:00Z',
    not_after: '2027-01-01T00:00:00Z',
    certificate_count: 1,
    valid: true,
    errors: [],
  },
  connection_test: {
    tested_at: '2026-07-28T12:00:00Z',
    success: true,
    duration_ms: 18,
    tested_by: 'superadmin',
  },
  updated_at: '2026-07-28T12:00:00Z',
  updated_by: 'superadmin',
};

describe('LdapConfiguracaoPage', () => {
  let fixture: ComponentFixture<LdapConfiguracaoPage>;
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
    fixture = TestBed.createComponent(LdapConfiguracaoPage);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('projeta status e metadados sem receber a senha de bind', async () => {
    fixture.detectChanges();
    httpMock.expectOne(apiConfig.routes.settingsLdap).flush(CONFIGURATION);
    await fixture.whenStable();
    fixture.detectChanges();

    const text = fixture.nativeElement.textContent;
    const password = fixture.nativeElement.querySelector(
      '#bind_password',
    ) as HTMLInputElement;
    expect(text).toContain('LDAP e autenticação');
    expect(text).toContain('Corporate CA');
    expect(text).toContain('configurada');
    expect(password.value).toBe('');
    expect(text).not.toContain('segredo');
    expect(
      fixture.nativeElement.querySelectorAll(
        '.servidor-grid > .campo',
      ).length,
    ).toBe(3);
  });

  it('envia a versão no salvamento auditado sem justificativa manual', async () => {
    fixture.detectChanges();
    httpMock.expectOne(apiConfig.routes.settingsLdap).flush(CONFIGURATION);
    await fixture.whenStable();
    fixture.detectChanges();

    const form = fixture.nativeElement.querySelector('form') as HTMLFormElement;
    form.dispatchEvent(new Event('submit'));

    const request = httpMock.expectOne(apiConfig.routes.settingsLdap);
    expect(request.request.method).toBe('PUT');
    expect(request.request.body.version).toBe(3);
    expect(request.request.body.reason).toBeUndefined();
    expect(request.request.body.bind_password).toBe('');
    expect(request.request.body.server_address).toBe('ad.example.internal');
    expect(request.request.body.use_tls).toBe(true);
    request.flush({ ...CONFIGURATION, version: 4 });
  });

  it('usa uma única escolha de TLS e alerta quando o transporte está sem criptografia', async () => {
    fixture.detectChanges();
    httpMock.expectOne(apiConfig.routes.settingsLdap).flush(CONFIGURATION);
    await fixture.whenStable();
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).not.toContain(
      'a credencial técnica e as senhas dos usuários',
    );

    fixture.componentInstance.formulario.controls.use_tls.setValue(false);
    fixture.detectChanges();

    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('Sem TLS');
    expect(text).toContain('a credencial técnica e as senhas dos usuários');
    expect(text).toContain('Descoberta e autenticação usarão este mesmo transporte');
    expect(text).not.toContain('Permitir LDAP simples somente no DEV');
    expect(text).not.toContain('Negociar StartTLS');
  });

  it('abre a busca em modal, exige dois caracteres e preenche o DN obrigatório', async () => {
    fixture.detectChanges();
    httpMock.expectOne(apiConfig.routes.settingsLdap).flush(CONFIGURATION);
    await fixture.whenStable();
    fixture.detectChanges();

    const campoDn = fixture.nativeElement.querySelector(
      '#required_group_dn',
    ) as HTMLInputElement;
    const acaoDn = campoDn.closest('.grupo-dn__acao') as HTMLElement;
    expect(acaoDn.textContent).toContain('Buscar grupo');

    fixture.componentInstance.abrirBuscaGrupos();
    expect(fixture.componentInstance.dialogoBuscaGrupoAberto()).toBe(true);

    fixture.componentInstance.buscaGrupo.setValue('s');
    fixture.componentInstance.buscarGrupos();
    httpMock.expectNone(apiConfig.routes.accountsDirectoryGroups);
    expect(fixture.componentInstance.erroBuscaGrupo()).toContain('dois caracteres');

    fixture.componentInstance.buscaGrupo.setValue('sg');
    fixture.componentInstance.buscarGrupos();
    httpMock
      .expectOne(
        (request) =>
          request.url === apiConfig.routes.accountsDirectoryGroups &&
          request.params.get('q') === 'sg',
      )
      .flush({
        limit: 50,
        results: [
          {
            distinguished_name: 'CN=SGPD,OU=Grupos,DC=example,DC=internal',
            name: 'SGPD',
            account_name: 'SGPD',
            description: 'Acesso SGPD',
          },
        ],
      });

    fixture.componentInstance.selecionarGrupo(fixture.componentInstance.gruposEncontrados()[0]);
    expect(fixture.componentInstance.formulario.controls.required_group_dn.value).toBe(
      'CN=SGPD,OU=Grupos,DC=example,DC=internal',
    );
    expect(fixture.componentInstance.dialogoBuscaGrupoAberto()).toBe(false);
  });

  it('envia e valida a CA sem justificativa manual', async () => {
    fixture.detectChanges();
    httpMock.expectOne(apiConfig.routes.settingsLdap).flush(CONFIGURATION);
    await fixture.whenStable();
    fixture.detectChanges();

    const file = new File(['certificate'], 'corporate-ca.pem', {
      type: 'application/x-pem-file',
    });
    const input = fixture.nativeElement.querySelector('#certificate') as HTMLInputElement;
    Object.defineProperty(input, 'files', { value: [file] });
    input.dispatchEvent(new Event('change'));
    fixture.detectChanges();

    const button = [...fixture.nativeElement.querySelectorAll('button')].find((candidate) =>
      candidate.textContent.includes('Validar e enviar CA'),
    ) as HTMLButtonElement;
    button.click();

    const request = httpMock.expectOne(apiConfig.routes.settingsLdapCertificate);
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toBeInstanceOf(FormData);
    const formData = request.request.body as FormData;
    expect(formData.get('version')).toBe('3');
    expect((formData.get('certificate') as File).name).toBe('corporate-ca.pem');
    expect(formData.has('reason')).toBe(false);
    request.flush({ ...CONFIGURATION, version: 4 });
    await fixture.whenStable();
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain(
      'Certificado validado, armazenado em área privada e auditado.',
    );
  });
});
