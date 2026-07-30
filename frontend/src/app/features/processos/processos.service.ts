import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { apiConfig } from '../../core/config/api.config';
import {
  ListaProcessos,
  ListaTarefasConcluidasProcesso,
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

  listarTarefasConcluidas(processUuid: string): Observable<ListaTarefasConcluidasProcesso> {
    const params = new HttpParams().set('status', 'CONCLUIDA').set('limit', 100);
    return this.http.get<ListaTarefasConcluidasProcesso>(
      `${apiConfig.routes.processes}${processUuid}/tasks/`,
      { params },
    );
  }
}
