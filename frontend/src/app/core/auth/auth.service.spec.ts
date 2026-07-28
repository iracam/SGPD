import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideHttpClient } from '@angular/common/http';
import { TestBed } from '@angular/core/testing';
import { describe, expect, it, beforeEach, afterEach } from 'vitest';

import { apiConfig } from '../config/api.config';
import { AuthService } from './auth.service';
import { AuthUser } from './models/auth.models';

const USER: AuthUser = {
  id: 1,
  username: 'api.user',
  email: 'api.user@example.invalid',
  first_name: 'Api',
  last_name: 'User',
  display_name: 'Api User',
  must_change_password: false,
  is_superuser: false,
};

describe('AuthService', () => {
  let service: AuthService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(AuthService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('começa anônimo', () => {
    expect(service.isAuthenticated()).toBe(false);
    expect(service.currentUser()).toBeNull();
  });

  it('guarda o usuário após o login', () => {
    service.login({ username: 'api.user', password: 'x' }).subscribe();
    httpMock.expectOne(apiConfig.routes.authLogin).flush(USER);

    expect(service.isAuthenticated()).toBe(true);
    expect(service.currentUser()?.display_name).toBe('Api User');
  });

  it('não persiste nada da sessão no armazenamento local', () => {
    service.login({ username: 'api.user', password: 'x' }).subscribe();
    httpMock.expectOne(apiConfig.routes.authLogin).flush(USER);

    const stored = Object.keys(localStorage).join(' ');
    expect(stored).not.toContain('user');
    expect(stored).not.toContain('token');
    expect(stored).not.toContain('session');
  });

  it('limpa o estado no logout', () => {
    service.login({ username: 'api.user', password: 'x' }).subscribe();
    httpMock.expectOne(apiConfig.routes.authLogin).flush(USER);

    service.logout().subscribe();
    httpMock.expectOne(apiConfig.routes.authLogout).flush({});

    expect(service.isAuthenticated()).toBe(false);
  });

  it('expõe a exigência de troca de senha temporária', () => {
    service.login({ username: 'api.user', password: 'x' }).subscribe();
    httpMock
      .expectOne(apiConfig.routes.authLogin)
      .flush({ ...USER, must_change_password: true });

    expect(service.mustChangePassword()).toBe(true);
  });

  it('deriva a visibilidade do menu do contexto do servidor', () => {
    service.loadContext().subscribe();
    httpMock.expectOne(apiConfig.routes.authContext).flush({
      user: USER,
      roles: ['DP'],
      permissions: {},
      scopes: { is_superuser: false, assignments: [] },
      features: {
        manage_users: { can_view: false },
        query_senior_references: { can_view: true },
      },
      meta: { policy: 'session', server_time: '2026-07-28T00:00:00Z' },
    });

    expect(service.canView('query_senior_references')).toBe(true);
    expect(service.canView('manage_users')).toBe(false);
    // Ausente do contexto: nega por padrão.
    expect(service.canView('view_account_audit')).toBe(false);
  });
});
