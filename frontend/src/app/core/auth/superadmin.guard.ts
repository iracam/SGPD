import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { catchError, map, of } from 'rxjs';

import { AuthService } from './auth.service';

/** Orienta a navegação; a API repete a decisão exclusivamente por is_superuser. */
export const superadminGuard: CanActivateFn = () => {
  const authService = inject(AuthService);
  const router = inject(Router);

  return authService.ensureAuthenticated().pipe(
    map(() =>
      authService.currentUser()?.is_superuser
        ? true
        : router.createUrlTree(['/fe/painel']),
    ),
    catchError(() => of(router.createUrlTree(['/fe/login']))),
  );
};
