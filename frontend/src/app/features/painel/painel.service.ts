import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { apiConfig } from '../../core/config/api.config';
import { Indicadores } from './models/painel.models';

@Injectable({ providedIn: 'root' })
export class PainelService {
  private readonly http = inject(HttpClient);

  indicadores(): Observable<Indicadores> {
    return this.http.get<Indicadores>(apiConfig.routes.reportingDashboard);
  }
}
