import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { apiConfig } from '../../core/config/api.config';
import {
  ListaProcessos,
  ListaTarefasProcesso,
} from './models/processos.models';

@Injectable({ providedIn: 'root' })
export class ProcessosService {
  private readonly http = inject(HttpClient);

  listarRascunhos(): Observable<ListaProcessos> {
    const params = new HttpParams().set('status', 'RASCUNHO').set('limit', 50);
    return this.http.get<ListaProcessos>(apiConfig.routes.processes, { params });
  }

  listarConcluidos(): Observable<ListaProcessos> {
    const params = new HttpParams().set('completed', true).set('limit', 50);
    return this.http.get<ListaProcessos>(apiConfig.routes.processes, { params });
  }

  listarEmAberto(): Observable<ListaProcessos> {
    const params = new HttpParams().set('open', true).set('limit', 50);
    return this.http.get<ListaProcessos>(apiConfig.routes.processes, { params });
  }

  listarTarefas(
    processUuid: string,
    apenasConcluidas: boolean,
  ): Observable<ListaTarefasProcesso> {
    let params = new HttpParams().set('limit', 100);
    if (apenasConcluidas) {
      params = params.set('status', 'CONCLUIDA');
    }
    return this.http.get<ListaTarefasProcesso>(
      `${apiConfig.routes.processes}${processUuid}/tasks/`,
      { params },
    );
  }
}
