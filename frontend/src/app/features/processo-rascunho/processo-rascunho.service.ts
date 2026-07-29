import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { apiConfig } from '../../core/config/api.config';
import {
  AtualizacaoSelecaoRascunho,
  ContextoRascunho,
} from './models/processo-rascunho.models';

@Injectable({ providedIn: 'root' })
export class ProcessoRascunhoService {
  private readonly http = inject(HttpClient);

  obter(uuid: string): Observable<ContextoRascunho> {
    return this.http.get<ContextoRascunho>(this.draftUrl(uuid));
  }

  salvarSelecao(
    uuid: string,
    payload: AtualizacaoSelecaoRascunho,
  ): Observable<ContextoRascunho> {
    return this.http.put<ContextoRascunho>(
      `${this.draftUrl(uuid)}selection/`,
      payload,
    );
  }

  iniciar(
    uuid: string,
    expectedVersion: number,
    idempotencyKey: string,
  ): Observable<ContextoRascunho> {
    const headers = new HttpHeaders().set('Idempotency-Key', idempotencyKey);
    return this.http.post<ContextoRascunho>(
      `${apiConfig.routes.processes}${uuid}/start/`,
      { expected_version: expectedVersion },
      { headers },
    );
  }

  private draftUrl(uuid: string): string {
    return `${apiConfig.routes.processes}${uuid}/draft/`;
  }
}
