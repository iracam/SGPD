/**
 * O armazenamento local guarda apenas preferências de interface. Nenhum dado de
 * sessão ou identidade é persistido no navegador (ADR-026).
 */
export const STORAGE_KEYS = {
  theme: 'sgpd.theme',
  navCollapsed: 'sgpd.layout.nav-collapsed',
} as const;

/** Códigos do envelope de erro da API que o cliente trata explicitamente. */
export const API_ERROR_CODES = {
  notAuthenticated: 'not_authenticated',
  invalidCredentials: 'invalid_credentials',
  permissionDenied: 'permission_denied',
  passwordChangeRequired: 'password_change_required',
  validationError: 'validation_error',
  throttled: 'throttled',
} as const;
