import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import { apiConfig } from '../config/api.config';
import { AuthenticatedLayout } from './authenticated-layout';

function contextWith(
  features: Record<string, { can_view: boolean }>,
  isSuperuser = false,
  roles: string[] = [],
) {
  return {
    user: {
      id: 1,
      username: 'api.user',
      email: 'api.user@example.invalid',
      first_name: 'Api',
      last_name: 'User',
      display_name: 'Api User',
      must_change_password: false,
      is_superuser: isSuperuser,
    },
    roles,
    permissions: {},
    scopes: { is_superuser: isSuperuser, assignments: [] },
    features,
    meta: { policy: 'session', server_time: '2026-07-28T00:00:00Z' },
  };
}

describe('AuthenticatedLayout', () => {
  let fixture: ComponentFixture<AuthenticatedLayout>;
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
    fixture = TestBed.createComponent(AuthenticatedLayout);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  function labels(): string[] {
    return Array.from(
      fixture.nativeElement.querySelectorAll('.nav__label') as NodeListOf<HTMLElement>,
    ).map((element) => element.textContent?.trim() ?? '');
  }

  it('mostra apenas o painel quando o contexto nega tudo', async () => {
    fixture.detectChanges();
    httpMock.expectOne(apiConfig.routes.authContext).flush(
      contextWith({
        manage_users: { can_view: false },
        manage_roles: { can_view: false },
        view_account_audit: { can_view: false },
        query_senior_references: { can_view: false },
        manage_sectors: { can_view: false },
      }),
    );
    await fixture.whenStable();
    fixture.detectChanges();

    expect(labels()).toEqual(['Painel']);
  });

  it('revela cada item conforme a permissão concedida pelo servidor', async () => {
    fixture.detectChanges();
    httpMock.expectOne(apiConfig.routes.authContext).flush(
      contextWith(
        {
          manage_users: { can_view: true },
          manage_roles: { can_view: false },
          view_account_audit: { can_view: true },
          query_senior_references: { can_view: true },
          manage_sectors: { can_view: true },
        },
        false,
        ['DP'],
      ),
    );
    await fixture.whenStable();
    fixture.detectChanges();

    expect(labels()).toEqual([
      'Painel',
      'Processos',
      'Relatórios',
      'Notificações',
      'Setores',
      'Usuários',
      'Auditoria',
    ]);
  });

  it('mostra todos os menus e a seção Configurações para SuperAdmin', async () => {
    fixture.detectChanges();
    httpMock.expectOne(apiConfig.routes.authContext).flush(
      contextWith(
        {
          manage_users: { can_view: true },
          manage_roles: { can_view: true },
          view_account_audit: { can_view: true },
          query_senior_references: { can_view: true },
          manage_sectors: { can_view: true },
        },
        true,
      ),
    );
    await fixture.whenStable();
    fixture.detectChanges();

    expect(labels()).toEqual([
      'Painel',
      'Processos',
      'Minhas tarefas',
      'Relatórios',
      'Notificações',
      'Setores',
      'Grupos e templates',
      'Usuários',
      'Auditoria',
      'Configurações',
    ]);
    expect(fixture.nativeElement.querySelector('.nav-section__title')?.textContent.trim()).toBe(
      'Configurações',
    );
  });

  it('mostra Minhas tarefas somente para responsabilidade derivada de setor', async () => {
    fixture.detectChanges();
    httpMock.expectOne(apiConfig.routes.authContext).flush(
      contextWith(
        {
          manage_users: { can_view: false },
          manage_roles: { can_view: false },
          view_account_audit: { can_view: false },
          query_senior_references: { can_view: false },
          manage_sectors: { can_view: false },
        },
        false,
        ['RESPONSAVEL_SETOR'],
      ),
    );
    await fixture.whenStable();
    fixture.detectChanges();

    expect(labels()).toEqual(['Painel', 'Minhas tarefas']);
  });
});
