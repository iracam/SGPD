import { HttpErrorResponse } from '@angular/common/http';

import { ApiError } from '../auth/models/auth.models';

/** Chave que o backend usa para erros não vinculados a um campo. */
export const NON_FIELD_ERRORS = 'non_field_errors';

export type FieldErrors = Record<string, string[]>;

function body(error: unknown): ApiError | null {
  return error instanceof HttpErrorResponse ? ((error.error as ApiError) ?? null) : null;
}

/**
 * Traduz `details` do envelope da API em erros por campo, prontos para o
 * formulário. Aceita lista, string e contratos aninhados, preservando nesses
 * casos o caminho completo do campo (por exemplo, `initial_role.role_id`).
 */
export function fieldErrors(error: unknown): FieldErrors {
  const details = (body(error)?.details ?? {}) as Record<string, unknown>;
  const normalized: FieldErrors = {};

  const visit = (prefix: string, detail: unknown): void => {
    if (typeof detail === 'string') {
      normalized[prefix] = [detail];
      return;
    }
    if (Array.isArray(detail)) {
      normalized[prefix] = detail.map(String);
      return;
    }
    if (detail !== null && typeof detail === 'object') {
      for (const [field, nested] of Object.entries(detail)) {
        visit(prefix ? `${prefix}.${field}` : field, nested);
      }
    }
  };

  for (const [field, detail] of Object.entries(details)) {
    visit(field, detail);
  }
  return normalized;
}

/** Mensagem geral: erros sem campo primeiro, depois a mensagem do envelope. */
export function errorMessage(error: unknown, fallback = 'Não foi possível concluir a operação.'): string {
  const errors = fieldErrors(error);
  const semCampo = errors[NON_FIELD_ERRORS];
  if (semCampo?.length) {
    return semCampo.join(' ');
  }
  return body(error)?.message ?? fallback;
}

export function errorCode(error: unknown): string | null {
  return body(error)?.code ?? null;
}
