import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { apiConfig } from '../../core/config/api.config';
import {
  ConferenciaEncerramento,
  PreviaExclusao,
  ResultadoExclusao,
} from './models/processo-encerramento.models';

/**
 * Atos formais do ciclo (ADR-051).
 *
 * Toda transição leva versão esperada e `Idempotency-Key`; a resposta é sempre
 * a conferência inteira, com a prontidão recalculada pelo servidor.
 */
@Injectable({ providedIn: 'root' })
export class ProcessoEncerramentoService {
  private readonly http = inject(HttpClient);

  carregar(processUuid: string): Observable<ConferenciaEncerramento> {
    return this.http.get<ConferenciaEncerramento>(this.rota(processUuid, 'readiness'));
  }

  liberar(
    processUuid: string,
    payload: { expected_version: number; notes: string; override_reason?: string },
    idempotencyKey: string,
  ): Observable<ConferenciaEncerramento> {
    return this.transicao(processUuid, 'release', payload, idempotencyKey);
  }

  registrarProcessamento(
    processUuid: string,
    payload: {
      expected_version: number;
      termination_reference: string;
      processed_on: string;
      notes: string;
    },
    idempotencyKey: string,
  ): Observable<ConferenciaEncerramento> {
    return this.transicao(processUuid, 'processing', payload, idempotencyKey);
  }

  encerrar(
    processUuid: string,
    payload: { expected_version: number; notes: string; override_reason?: string },
    idempotencyKey: string,
  ): Observable<ConferenciaEncerramento> {
    return this.transicao(processUuid, 'close', payload, idempotencyKey);
  }

  cancelar(
    processUuid: string,
    payload: { expected_version: number; reason: string },
    idempotencyKey: string,
  ): Observable<ConferenciaEncerramento> {
    return this.transicao(processUuid, 'cancel', payload, idempotencyKey);
  }

  reabrir(
    processUuid: string,
    payload: { expected_version: number; reason: string; task_ids: number[] },
    idempotencyKey: string,
  ): Observable<ConferenciaEncerramento> {
    return this.transicao(processUuid, 'reopen', payload, idempotencyKey);
  }

  /**
   * Prévia da exclusão (ADR-056): o que será destruído, antes de confirmar.
   *
   * É leitura pura, e a decisão que ela antecipa é sempre refeita pelo servidor
   * sob lock — esta tela avisa, não autoriza.
   */
  previaExclusao(processUuid: string): Observable<PreviaExclusao> {
    return this.http.get<PreviaExclusao>(this.rota(processUuid, 'purge'));
  }

  /** Exclusão definitiva. Não há desfazer: só resta a lápide que volta aqui. */
  excluir(
    processUuid: string,
    payload: { expected_version: number; reason: string },
    idempotencyKey: string,
  ): Observable<ResultadoExclusao> {
    return this.http.post<ResultadoExclusao>(this.rota(processUuid, 'purge'), payload, {
      headers: new HttpHeaders().set('Idempotency-Key', idempotencyKey),
    });
  }

  private transicao(
    processUuid: string,
    action: string,
    payload: Record<string, unknown>,
    idempotencyKey: string,
  ): Observable<ConferenciaEncerramento> {
    return this.http.post<ConferenciaEncerramento>(this.rota(processUuid, action), payload, {
      headers: new HttpHeaders().set('Idempotency-Key', idempotencyKey),
    });
  }

  private rota(processUuid: string, action: string): string {
    return `${apiConfig.routes.processes}${processUuid}/${action}/`;
  }
}
