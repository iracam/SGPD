import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { apiConfig } from '../../core/config/api.config';
import { Operacao } from './models/operacao.models';

@Injectable({ providedIn: 'root' })
export class OperacaoService {
  private readonly http = inject(HttpClient);

  estado(): Observable<Operacao> {
    return this.http.get<Operacao>(apiConfig.routes.reportingOperations);
  }
}
