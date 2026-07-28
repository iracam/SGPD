import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';

import { API_ERROR_CODES } from './auth.constants';
import { SKIP_AUTH_REDIRECT } from './auth.context';
import { AuthService } from './auth.service';
import { ApiError } from './models/auth.models';

/**
 * Reage aos dois códigos do envelope que mudam para onde o usuário deve estar.
 * Não há refresh de token a fazer: a sessão é do servidor (ADR-026).
 */
export const authInterceptor: HttpInterceptorFn = (request, next) => {
  const authService = inject(AuthService);
  const router = inject(Router);

  return next(request).pipe(
    catchError((error: unknown) => {
      if (!(error instanceof HttpErrorResponse) || request.context.get(SKIP_AUTH_REDIRECT)) {
        return throwError(() => error);
      }

      if (error.status === 401) {
        authService.clear();
        void router.navigateByUrl('/fe/login');
        return throwError(() => error);
      }

      const body = error.error as ApiError | null;
      if (error.status === 403 && body?.code === API_ERROR_CODES.passwordChangeRequired) {
        void router.navigateByUrl('/fe/senha');
      }

      return throwError(() => error);
    }),
  );
};
