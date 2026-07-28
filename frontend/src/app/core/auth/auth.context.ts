import { HttpContextToken } from '@angular/common/http';

/** Impede que o interceptador reaja ao 401 esperado de uma sondagem de sessão. */
export const SKIP_AUTH_REDIRECT = new HttpContextToken<boolean>(() => false);
