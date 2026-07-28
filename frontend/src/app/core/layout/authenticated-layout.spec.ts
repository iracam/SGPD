import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import { apiConfig } from '../config/api.config';
import { AuthenticatedLayout } from './authenticated-layout';

function contextWith(features: Record<string, { can_view: boolean }>) {
  return {
    user: {
      id: 1,
      username: 'api.user',
      email: 'api.user@example.invalid',
      first_name: 'Api',
      last_name: 'User',
      display_name: 'Api User',
      must_change_password: false,
      is_superuser: false,
    },
    roles: [],
    permissions: {},
    scopes: { is_superuser: false, assignments: [] },
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
      }),
    );
    await fixture.whenStable();
    fixture.detectChanges();

    expect(labels()).toEqual(['Painel']);
  });

  it('revela cada item conforme a permissão concedida pelo servidor', async () => {
    fixture.detectChanges();
    httpMock.expectOne(apiConfig.routes.authContext).flush(
      contextWith({
        manage_users: { can_view: true },
        manage_roles: { can_view: false },
        view_account_audit: { can_view: true },
        query_senior_references: { can_view: true },
      }),
    );
    await fixture.whenStable();
    fixture.detectChanges();

    expect(labels()).toEqual(['Painel', 'Colaboradores', 'Usuários', 'Auditoria']);
  });
});
