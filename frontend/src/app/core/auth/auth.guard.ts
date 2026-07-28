import { inject } from '@angular/core';
import { CanActivateFn, Router, RouterStateSnapshot } from '@angular/router';
import { catchError, map, of } from 'rxjs';

import { AuthService } from './auth.service';

const CHANGE_PASSWORD_ROUTE = '/fe/senha';

/**
 * Exige sessão ativa e desvia para a troca de senha enquanto houver senha
 * temporária pendente. O servidor impõe a mesma regra: sem isso, a API responde
 * `403 password_change_required`.
 */
export const authGuard: CanActivateFn = (_route, state: RouterStateSnapshot) => {
  const authService = inject(AuthService);
  const router = inject(Router);

  return authService.ensureAuthenticated().pipe(
    map(() => {
      if (authService.mustChangePassword() && !state.url.startsWith(CHANGE_PASSWORD_ROUTE)) {
        return router.createUrlTree([CHANGE_PASSWORD_ROUTE]);
      }
      return true;
    }),
    catchError(() => of(router.createUrlTree(['/fe/login']))),
  );
};
