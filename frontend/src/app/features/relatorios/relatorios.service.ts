import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { apiConfig } from '../../core/config/api.config';
import { Relatorios } from './models/relatorios.models';

@Injectable({ providedIn: 'root' })
export class RelatoriosService {
  private readonly http = inject(HttpClient);

  consultar(start: string, end: string): Observable<Relatorios> {
    let params = new HttpParams();
    if (start) {
      params = params.set('start', start);
    }
    if (end) {
      params = params.set('end', end);
    }
    return this.http.get<Relatorios>(apiConfig.routes.reportingReports, { params });
  }
}
