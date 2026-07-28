import { firstValueFrom, of } from 'rxjs';
import { catchError, switchMap } from 'rxjs/operators';

import { AuthService } from './auth.service';

/**
 * Antes do primeiro render: garante o cookie CSRF e restaura a sessão, se
 * houver. Um 401 aqui é resultado normal, não erro.
 */
export function authInitializer(authService: AuthService): () => Promise<void> {
  return async () => {
    await firstValueFrom(
      authService.ensureCsrfCookie().pipe(
        switchMap(() => authService.restoreSession()),
        switchMap(() => authService.loadContext().pipe(catchError(() => of(null)))),
        catchError(() => of(null)),
      ),
    );
  };
}
