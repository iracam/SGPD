import { HttpErrorResponse } from '@angular/common/http';
import { describe, expect, it } from 'vitest';

import { errorCode, errorMessage, fieldErrors } from './api-error';

function resposta(body: unknown, status = 400): HttpErrorResponse {
  return new HttpErrorResponse({ error: body, status, statusText: 'Erro' });
}

describe('api-error', () => {
  it('traduz details em erros por campo', () => {
    const erro = resposta({
      code: 'validation_error',
      message: 'Os dados enviados são inválidos.',
      details: { email: ['E-mail já utilizado.'], reason: ['Campo obrigatório.'] },
    });

    expect(fieldErrors(erro)).toEqual({
      email: ['E-mail já utilizado.'],
      reason: ['Campo obrigatório.'],
    });
  });

  it('aceita detalhe em string, como o backend às vezes devolve', () => {
    const erro = resposta({ code: 'validation_error', message: 'x', details: { email: 'Inválido.' } });

    expect(fieldErrors(erro)).toEqual({ email: ['Inválido.'] });
  });

  it('achata erros de contratos aninhados mantendo o caminho do campo', () => {
    const erro = resposta({
      code: 'validation_error',
      message: 'Os dados enviados são inválidos.',
      details: {
        initial_role: {
          branch_code: ['Informe empresa e filial para esse escopo.'],
        },
      },
    });

    expect(fieldErrors(erro)).toEqual({
      'initial_role.branch_code': ['Informe empresa e filial para esse escopo.'],
    });
  });

  it('devolve objeto vazio quando não há details', () => {
    expect(fieldErrors(resposta({ code: 'permission_denied', message: 'Negado.' }))).toEqual({});
  });

  it('prioriza erros sem campo na mensagem geral', () => {
    const erro = resposta({
      code: 'validation_error',
      message: 'Genérica.',
      details: { non_field_errors: ['A senha atual está incorreta.'] },
    });

    expect(errorMessage(erro)).toBe('A senha atual está incorreta.');
  });

  it('cai para a mensagem do envelope quando não há erro sem campo', () => {
    const erro = resposta({ code: 'permission_denied', message: 'Usuário sem permissão.' });

    expect(errorMessage(erro)).toBe('Usuário sem permissão.');
  });

  it('usa o texto alternativo quando a resposta não é um envelope', () => {
    expect(errorMessage(new Error('falha de rede'), 'Sem conexão.')).toBe('Sem conexão.');
  });

  it('expõe o código para controle de fluxo', () => {
    expect(errorCode(resposta({ code: 'password_change_required', message: 'x' }, 403)))
      .toBe('password_change_required');
    expect(errorCode(new Error('x'))).toBeNull();
  });
});
