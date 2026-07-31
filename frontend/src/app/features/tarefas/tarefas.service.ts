import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { apiConfig } from '../../core/config/api.config';
import {
  ConcluirTarefaPayload,
  CriarPendenciaPayload,
  DecisaoValor,
  Evidencia,
  ListaTarefas,
  Pendencia,
  PendenciaStatus,
  TarefaSetor,
} from './models/tarefas.models';

@Injectable({ providedIn: 'root' })
export class TarefasService {
  private readonly http = inject(HttpClient);

  listar(): Observable<ListaTarefas> {
    return this.http.get<ListaTarefas>(apiConfig.routes.tasks);
  }

  iniciar(
    taskId: number,
    expectedVersion: number,
    idempotencyKey: string,
  ): Observable<TarefaSetor> {
    return this.http.post<TarefaSetor>(
      `${apiConfig.routes.tasks}${taskId}/start/`,
      { expected_version: expectedVersion },
      { headers: this.headers(idempotencyKey) },
    );
  }

  concluir(
    taskId: number,
    payload: ConcluirTarefaPayload,
    idempotencyKey: string,
  ): Observable<TarefaSetor> {
    return this.http.post<TarefaSetor>(
      `${apiConfig.routes.tasks}${taskId}/complete/`,
      payload,
      { headers: this.headers(idempotencyKey) },
    );
  }

  criarPendencia(
    payload: CriarPendenciaPayload,
    idempotencyKey: string,
  ): Observable<Pendencia> {
    return this.http.post<Pendencia>(apiConfig.routes.pendingItems, payload, {
      headers: this.headers(idempotencyKey),
    });
  }

  alterarPendencia(
    pendingUuid: string,
    expectedVersion: number,
    status: PendenciaStatus,
    comment: string,
    idempotencyKey: string,
  ): Observable<Pendencia> {
    return this.http.post<Pendencia>(
      `${apiConfig.routes.pendingItems}${pendingUuid}/status/`,
      { expected_version: expectedVersion, status, comment },
      { headers: this.headers(idempotencyKey) },
    );
  }

  comentarPendencia(
    pendingUuid: string,
    expectedVersion: number,
    comment: string,
    idempotencyKey: string,
  ): Observable<Pendencia> {
    return this.http.post<Pendencia>(
      `${apiConfig.routes.pendingItems}${pendingUuid}/comments/`,
      { expected_version: expectedVersion, comment },
      { headers: this.headers(idempotencyKey) },
    );
  }

  informarValor(
    pendingUuid: string,
    expectedVersion: number,
    payload: { amount_informed: string; justification: string },
    idempotencyKey: string,
  ): Observable<Pendencia> {
    return this.postValor(
      pendingUuid,
      '',
      { ...payload, expected_version: expectedVersion },
      idempotencyKey,
    );
  }

  apurarValor(
    pendingUuid: string,
    expectedVersion: number,
    payload: { amount_assessed: string; justification: string },
    idempotencyKey: string,
  ): Observable<Pendencia> {
    return this.postValor(
      pendingUuid,
      'assessment/',
      { ...payload, expected_version: expectedVersion },
      idempotencyKey,
    );
  }

  contestarValor(
    pendingUuid: string,
    expectedVersion: number,
    payload: { amount_contested: string; justification: string },
    idempotencyKey: string,
  ): Observable<Pendencia> {
    return this.postValor(
      pendingUuid,
      'contestation/',
      { ...payload, expected_version: expectedVersion },
      idempotencyKey,
    );
  }

  decidirValor(
    pendingUuid: string,
    expectedVersion: number,
    payload: { decision: DecisaoValor; opinion: string; amount_approved?: string },
    idempotencyKey: string,
  ): Observable<Pendencia> {
    return this.postValor(
      pendingUuid,
      'decision/',
      { ...payload, expected_version: expectedVersion },
      idempotencyKey,
    );
  }

  enviarEvidencia(
    taskId: number,
    expectedTaskVersion: number,
    file: File,
    idempotencyKey: string,
    checklistItemId?: number,
    pendingUuid?: string,
  ): Observable<Evidencia> {
    const body = new FormData();
    body.set('task_id', String(taskId));
    body.set('expected_task_version', String(expectedTaskVersion));
    body.set('classification', 'RESTRITA');
    body.set('file', file);
    if (checklistItemId !== undefined) {
      body.set('checklist_item_id', String(checklistItemId));
    }
    if (pendingUuid !== undefined) {
      body.set('pending_uuid', pendingUuid);
    }
    return this.http.post<Evidencia>(apiConfig.routes.evidence, body, {
      headers: this.headers(idempotencyKey),
    });
  }

  /** O eixo de valor mora sob `<uuid>/amount/`; a resposta é sempre a pendência inteira. */
  private postValor(
    pendingUuid: string,
    suffix: string,
    body: Record<string, unknown>,
    idempotencyKey: string,
  ): Observable<Pendencia> {
    return this.http.post<Pendencia>(
      `${apiConfig.routes.pendingItems}${pendingUuid}/amount/${suffix}`,
      body,
      { headers: this.headers(idempotencyKey) },
    );
  }

  private headers(idempotencyKey: string): HttpHeaders {
    return new HttpHeaders().set('Idempotency-Key', idempotencyKey);
  }
}
