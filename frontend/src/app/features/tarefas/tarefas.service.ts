import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { apiConfig } from '../../core/config/api.config';
import {
  ConcluirTarefaPayload,
  ListaTarefas,
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

  private headers(idempotencyKey: string): HttpHeaders {
    return new HttpHeaders().set('Idempotency-Key', idempotencyKey);
  }
}
