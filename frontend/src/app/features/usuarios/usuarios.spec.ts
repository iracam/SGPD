import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { provideRouter, Router } from '@angular/router';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { apiConfig } from '../../core/config/api.config';
import { AuthService } from '../../core/auth/auth.service';
import { Usuario, UsuarioDiretorio } from './models/usuarios.models';
import { UsuariosPage } from './usuarios';

const USUARIO: Usuario = {
  id: 1,
  username: 'api.comum',
  email: 'api.comum@example.invalid',
  first_name: 'Api',
  last_name: 'Comum',
  display_name: 'Api Comum',
  must_change_password: false,
  is_superuser: false,
  is_active: true,
  version: 1,
  date_joined: null,
  last_login: null,
  ad_identifier: null,
  ad_username: null,
  ad_linked_at: null,
  ad_linked_by: null,
  ad_authentication_enabled: false,
  local_password_allowed: true,
};

const USUARIO_AD: UsuarioDiretorio = {
  identifier: '0899b887-704b-4c59-ae09-3a678a4e02a1',
  username: 'maria.silva',
  user_principal_name: 'maria.silva@example.internal',
  first_name: 'Maria',
  last_name: 'Silva',
  display_name: 'Maria Silva',
  email: 'maria.silva@example.internal',
  distinguished_name: 'CN=Maria Silva,OU=Usuarios,DC=example,DC=internal',
  can_import: true,
  missing_import_fields: [],
  local_user: null,
  username_conflict: null,
  email_conflict: null,
};

describe('UsuariosPage', () => {
  let fixture: ComponentFixture<UsuariosPage>;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        provideAnimationsAsync(),
      ],
    });
    fixture = TestBed.createComponent(UsuariosPage);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  function responder(usuarios: Usuario[]): void {
    fixture.detectChanges();
    const req = httpMock.expectOne((r) => r.url === apiConfig.routes.accountsUsers);
    req.flush({ offset: 0, limit: 50, results: usuarios });
    fixture.detectChanges();
  }

  it('renderiza os mesmos dados como cartão e como linha de tabela', () => {
    responder([USUARIO]);

    // A ADR-028 exige as duas representações; a visibilidade é decidida por CSS.
    expect(fixture.nativeElement.querySelectorAll('.cartao').length).toBe(1);
    expect(fixture.nativeElement.querySelectorAll('.tabela tbody tr').length).toBe(1);
  });

  it('anuncia lista vazia em vez de deixar a tela em branco', () => {
    responder([]);

    expect(fixture.nativeElement.querySelector('.vazio')).not.toBeNull();
  });

  it('marca senha temporária e conta inativa', () => {
    responder([{ ...USUARIO, must_change_password: true, is_active: false }]);

    const selos = fixture.nativeElement.textContent as string;
    expect(selos).toContain('Senha temporária');
    expect(selos).toContain('Inativo');
  });

  it('cria usuário local sem exigir ou enviar justificativa manual', () => {
    vi.spyOn(TestBed.inject(Router), 'navigate').mockResolvedValue(true);
    responder([]);
    fixture.componentInstance.abrirDialogo();
    fixture.componentInstance.formulario.setValue({
      username: 'novo.local',
      first_name: 'Novo',
      last_name: 'Local',
      email: 'novo.local@example.invalid',
      password: 'Temporaria-local!2026',
      password_confirm: 'Temporaria-local!2026',
      must_change_password: true,
      role_id: null,
      scope_type: 'GLOBAL',
      company_code: null,
      branch_code: null,
    });
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('label[for="reason"]')).toBeNull();

    const createButton = Array.from(
      fixture.nativeElement.querySelectorAll('button') as NodeListOf<HTMLButtonElement>,
    ).find((button) => button.textContent?.includes('Criar usuário'));
    createButton?.click();
    fixture.detectChanges();

    const createRequest = httpMock.expectOne(
      (request) =>
        request.url === apiConfig.routes.accountsUsers && request.method === 'POST',
    );
    expect(createRequest.request.body).toEqual({
      username: 'novo.local',
      first_name: 'Novo',
      last_name: 'Local',
      email: 'novo.local@example.invalid',
      password: 'Temporaria-local!2026',
      password_confirm: 'Temporaria-local!2026',
      must_change_password: true,
    });
    createRequest.flush({ ...USUARIO, username: 'novo.local' });
  });

  it('designa o papel inicial no mesmo cadastro e abre o detalhe criado', () => {
    vi.spyOn(TestBed.inject(AuthService), 'canView').mockImplementation(
      (permission) => permission === 'manage_roles',
    );
    vi.spyOn(TestBed.inject(Router), 'navigate').mockResolvedValue(true);
    responder([]);

    fixture.componentInstance.abrirDialogo();
    httpMock
      .expectOne(
        (request) =>
          request.url === apiConfig.routes.accountsRoles &&
          request.params.get('limit') === '200',
      )
      .flush({
        offset: 0,
        limit: 200,
        results: [
          {
            id: 7,
            code: 'DP',
            name: 'Departamento Pessoal',
            description: '',
            is_active: true,
            version: 1,
            permissions: [],
          },
        ],
      });
    fixture.componentInstance.formulario.setValue({
      username: 'novo.dp',
      first_name: 'Novo',
      last_name: 'DP',
      email: 'novo.dp@example.invalid',
      password: 'Temporaria-local!2026',
      password_confirm: 'Temporaria-local!2026',
      must_change_password: true,
      role_id: 7,
      scope_type: 'COMPANY',
      company_code: 1,
      branch_code: null,
    });
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('label[for="initial_role"]')).not.toBeNull();
    expect(fixture.nativeElement.querySelector('label[for="initial_role_reason"]')).toBeNull();

    const createButton = Array.from(
      fixture.nativeElement.querySelectorAll('button') as NodeListOf<HTMLButtonElement>,
    ).find((button) => button.textContent?.includes('Criar usuário'));
    createButton?.click();
    fixture.detectChanges();

    const createRequest = httpMock.expectOne(
      (request) =>
        request.url === apiConfig.routes.accountsUsers && request.method === 'POST',
    );
    expect(createRequest.request.body).toEqual({
      username: 'novo.dp',
      first_name: 'Novo',
      last_name: 'DP',
      email: 'novo.dp@example.invalid',
      password: 'Temporaria-local!2026',
      password_confirm: 'Temporaria-local!2026',
      must_change_password: true,
      initial_role: {
        role_id: 7,
        scope_type: 'COMPANY',
        company_code: 1,
        branch_code: null,
        valid_until: null,
      },
    });
    createRequest.flush({ ...USUARIO, id: 12, username: 'novo.dp' });
    expect(TestBed.inject(Router).navigate).toHaveBeenCalledWith(['/fe/usuarios', 12]);
  });

  it('exibe a mensagem do envelope quando a listagem falha', () => {
    fixture.detectChanges();
    httpMock
      .expectOne((r) => r.url === apiConfig.routes.accountsUsers)
      .flush(
        { code: 'permission_denied', message: 'Usuário sem permissão para esta operação.' },
        { status: 403, statusText: 'Forbidden' },
      );
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain('Usuário sem permissão');
  });

  it('busca usuários respeitando somente os filtros salvos no servidor', () => {
    responder([]);
    fixture.componentInstance.abrirDialogoAd();
    httpMock.expectOne(apiConfig.routes.accountsDirectoryStatus).flush({
      enabled: true,
      authentication_enabled: false,
      configured: true,
      secure_transport: true,
      insecure_transport: false,
      user_search_base_configured: true,
      group_search_base_configured: true,
      required_group_configured: false,
      errors: [],
    });

    fixture.componentInstance.buscaUsuarioAd.setValue('maria');
    fixture.componentInstance.buscarUsuariosAd();
    httpMock
      .expectOne(
        (request) =>
          request.url === apiConfig.routes.accountsDirectoryUsers &&
          request.params.get('q') === 'maria' &&
          !request.params.has('group_dn'),
      )
      .flush({ limit: 50, results: [USUARIO_AD] });

    expect(fixture.componentInstance.usuariosAd()).toEqual([USUARIO_AD]);
  });

  it('alerta que o transporte sem TLS também expõe senhas de login', () => {
    responder([]);
    fixture.componentInstance.abrirDialogoAd();
    httpMock.expectOne(apiConfig.routes.accountsDirectoryStatus).flush({
      enabled: true,
      authentication_enabled: false,
      configured: true,
      secure_transport: false,
      insecure_transport: true,
      user_search_base_configured: true,
      group_search_base_configured: true,
      required_group_configured: true,
      errors: [],
    });
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain('LDAP sem TLS');
    expect(fixture.nativeElement.textContent).toContain(
      'A credencial técnica e as senhas dos usuários',
    );
    expect(fixture.nativeElement.textContent).not.toContain('Grupo opcional');
  });

  it('importa a identidade sem exigir ou enviar justificativa manual', () => {
    responder([]);
    vi.spyOn(TestBed.inject(Router), 'navigate').mockResolvedValue(true);

    fixture.componentInstance.criarDoAd(USUARIO_AD);
    const createRequest = httpMock.expectOne(apiConfig.routes.accountsDirectoryUserCreate);
    expect(createRequest.request.body).toEqual({ identifier: USUARIO_AD.identifier });
    createRequest.flush({
      ...USUARIO,
      id: 2,
      username: USUARIO_AD.username,
      email: USUARIO_AD.email,
      ad_identifier: USUARIO_AD.identifier,
      ad_username: USUARIO_AD.username,
      role_assignments: [],
    });
    httpMock
      .expectOne((request) => request.url === apiConfig.routes.accountsUsers)
      .flush({ offset: 0, limit: 50, results: [] });
  });

  it('desativa a criação e explica quais atributos obrigatórios faltam no AD', () => {
    responder([]);
    fixture.componentInstance.dialogoAdAberto.set(true);
    fixture.componentInstance.statusDiretorio.set({
      enabled: true,
      authentication_enabled: false,
      configured: true,
      secure_transport: true,
      insecure_transport: false,
      user_search_base_configured: true,
      group_search_base_configured: true,
      required_group_configured: false,
      errors: [],
    });
    fixture.componentInstance.usuariosAd.set([
      {
        ...USUARIO_AD,
        email: null,
        can_import: false,
        missing_import_fields: ['mail'],
      },
    ]);
    fixture.detectChanges();

    const createButton = Array.from(
      fixture.nativeElement.querySelectorAll('button') as NodeListOf<HTMLButtonElement>,
    ).find((button) => button.textContent?.includes('Criar vinculada'));
    expect(createButton?.disabled).toBe(true);
    expect(fixture.nativeElement.textContent).toContain(
      'Não é possível criar: faltam no AD e-mail.',
    );
    expect(fixture.nativeElement.textContent).not.toContain(
      'Justificativa da criação/vinculação',
    );
  });
});
