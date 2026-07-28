import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import {
  ActivatedRouteSnapshot,
  GuardResult,
  RouterStateSnapshot,
  provideRouter,
} from '@angular/router';
import { firstValueFrom, isObservable, of } from 'rxjs';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import { apiConfig } from '../config/api.config';
import { authGuard } from './auth.guard';
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

function runGuard(url: string): Promise<GuardResult> {
  const result = TestBed.runInInjectionContext(() =>
    authGuard({} as ActivatedRouteSnapshot, { url } as RouterStateSnapshot),
  );
  return firstValueFrom(isObservable(result) ? result : of(result as GuardResult));
}

describe('authGuard', () => {
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    });
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('libera a rota quando há sessão', async () => {
    const pending = runGuard('/fe/painel');
    httpMock.expectOne(apiConfig.routes.authMe).flush(USER);

    expect(await pending).toBe(true);
  });

  it('manda para o login quando não há sessão', async () => {
    const pending = runGuard('/fe/painel');
    httpMock
      .expectOne(apiConfig.routes.authMe)
      .flush({ code: 'not_authenticated' }, { status: 401, statusText: 'Unauthorized' });

    expect(String(await pending)).toBe('/fe/login');
  });

  it('desvia para a troca enquanto a senha for temporária', async () => {
    const pending = runGuard('/fe/usuarios');
    httpMock
      .expectOne(apiConfig.routes.authMe)
      .flush({ ...USER, must_change_password: true });

    expect(String(await pending)).toBe('/fe/senha');
  });

  it('não desvia a própria tela de troca de senha', async () => {
    TestBed.inject(AuthService);
    const pending = runGuard('/fe/senha');
    httpMock
      .expectOne(apiConfig.routes.authMe)
      .flush({ ...USER, must_change_password: true });

    expect(await pending).toBe(true);
  });
});
