import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { apiConfig } from '../../core/config/api.config';
import { ConferenciaEncerramento } from './models/processo-encerramento.models';

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
    payload: { expected_version: number; notes: string },
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
    payload: { expected_version: number; notes: string },
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
