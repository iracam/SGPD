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
 * formulário. Aceita tanto lista quanto string, que é como o backend produz
 * dependendo da origem da validação.
 */
export function fieldErrors(error: unknown): FieldErrors {
  const details = body(error)?.details ?? {};
  const normalized: FieldErrors = {};
  for (const [field, messages] of Object.entries(details)) {
    normalized[field] = Array.isArray(messages) ? messages : [messages];
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
