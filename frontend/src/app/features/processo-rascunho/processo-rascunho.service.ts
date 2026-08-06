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

  /**
   * Exclusão definitiva do rascunho (ADR-056).
   *
   * Rascunho abandonado é o lixo mais comum da base, e aqui ele nunca produziu
   * nada: por isso a tela não pede a conferência do que será destruído — não há
   * o que destruir além do próprio rascunho. O servidor confere de novo.
   */
  excluir(
    uuid: string,
    expectedVersion: number,
    reason: string,
    idempotencyKey: string,
  ): Observable<unknown> {
    const headers = new HttpHeaders().set('Idempotency-Key', idempotencyKey);
    return this.http.post(
      `${apiConfig.routes.processes}${uuid}/purge/`,
      { expected_version: expectedVersion, reason },
      { headers },
    );
  }

  private draftUrl(uuid: string): string {
    return `${apiConfig.routes.processes}${uuid}/draft/`;
  }
}
