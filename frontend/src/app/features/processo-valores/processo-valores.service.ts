import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { apiConfig } from '../../core/config/api.config';
import { ConsolidacaoValores } from './models/processo-valores.models';

@Injectable({ providedIn: 'root' })
export class ProcessoValoresService {
  private readonly http = inject(HttpClient);

  consolidar(processUuid: string): Observable<ConsolidacaoValores> {
    return this.http.get<ConsolidacaoValores>(
      `${apiConfig.routes.processes}${processUuid}/amounts/`,
    );
  }
}
