import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { apiConfig } from '../../core/config/api.config';
import { FilaNotificacoes, Notificacao, NotificacaoStatus } from './models/notificacoes.models';

@Injectable({ providedIn: 'root' })
export class NotificacoesService {
  private readonly http = inject(HttpClient);

  listar(status: NotificacaoStatus | ''): Observable<FilaNotificacoes> {
    const params = status ? new HttpParams().set('status', status) : new HttpParams();
    return this.http.get<FilaNotificacoes>(apiConfig.routes.notifications, { params });
  }

  reprocessar(
    uuid: string,
    expectedVersion: number,
    idempotencyKey: string,
  ): Observable<Notificacao> {
    return this.http.post<Notificacao>(
      `${apiConfig.routes.notifications}${uuid}/reprocess/`,
      { expected_version: expectedVersion },
      { headers: new HttpHeaders().set('Idempotency-Key', idempotencyKey) },
    );
  }
}
