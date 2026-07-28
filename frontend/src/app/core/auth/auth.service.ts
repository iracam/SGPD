import { HttpClient, HttpContext } from '@angular/common/http';
import { Injectable, computed, inject, signal } from '@angular/core';
import { Observable, map, of, tap } from 'rxjs';

import { apiConfig } from '../config/api.config';
import { SKIP_AUTH_REDIRECT } from './auth.context';
import {
  AuthContext,
  AuthUser,
  ChangePasswordPayload,
  LoginPayload,
  PermissionKey,
} from './models/auth.models';

/**
 * Sessão Django com CSRF em origem única (ADR-026).
 *
 * O cookie de sessão é `HttpOnly` e nunca é lido aqui; o cabeçalho CSRF é
 * adicionado pelo próprio `HttpClient`, configurado em `app.config.ts`. Nada
 * relativo à sessão é gravado em `localStorage`: a fonte da verdade é sempre o
 * servidor.
 */
@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);

  private readonly userSignal = signal<AuthUser | null>(null);
  private readonly contextSignal = signal<AuthContext | null>(null);

  readonly currentUser = computed(() => this.userSignal());
  readonly currentContext = computed(() => this.contextSignal());
  readonly isAuthenticated = computed(() => this.userSignal() !== null);
  readonly mustChangePassword = computed(() => this.userSignal()?.must_change_password ?? false);

  /** Garante o cookie CSRF antes do primeiro envio. */
  ensureCsrfCookie(): Observable<void> {
    return this.http.get(apiConfig.routes.authCsrf).pipe(map(() => undefined));
  }

  login(payload: LoginPayload): Observable<AuthUser> {
    return this.http
      .post<AuthUser>(apiConfig.routes.authLogin, payload)
      .pipe(tap((user) => this.setUser(user)));
  }

  logout(): Observable<void> {
    return this.http.post<void>(apiConfig.routes.authLogout, {}).pipe(
      tap(() => this.clear()),
      map(() => undefined),
    );
  }

  loadCurrentUser(): Observable<AuthUser> {
    return this.http
      .get<AuthUser>(apiConfig.routes.authMe)
      .pipe(tap((user) => this.setUser(user)));
  }

  loadContext(): Observable<AuthContext> {
    return this.http
      .get<AuthContext>(apiConfig.routes.authContext)
      .pipe(tap((context) => this.contextSignal.set(context)));
  }

  changePassword(payload: ChangePasswordPayload): Observable<AuthUser> {
    return this.http
      .post<AuthUser>(apiConfig.routes.authChangePassword, payload)
      .pipe(tap((user) => this.setUser(user)));
  }

  /**
   * Sonda a sessão existente. O 401 é uma resposta esperada aqui, e não uma
   * falha: significa apenas que ninguém está autenticado.
   */
  restoreSession(): Observable<boolean> {
    return this.http
      .get<AuthUser>(apiConfig.routes.authMe, {
        context: new HttpContext().set(SKIP_AUTH_REDIRECT, true),
      })
      .pipe(
        tap((user) => this.setUser(user)),
        map(() => true),
      );
  }

  ensureAuthenticated(): Observable<boolean> {
    if (this.isAuthenticated()) {
      return of(true);
    }
    return this.restoreSession();
  }

  canView(permission: PermissionKey): boolean {
    return this.contextSignal()?.features[permission]?.can_view ?? false;
  }

  clear(): void {
    this.userSignal.set(null);
    this.contextSignal.set(null);
  }

  private setUser(user: AuthUser): void {
    this.userSignal.set(user);
  }
}
