import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { apiConfig } from '../../core/config/api.config';
import { Paginado } from '../usuarios/models/usuarios.models';
import { EventoAuditoria } from './models/auditoria.models';

@Injectable({ providedIn: 'root' })
export class AuditoriaService {
  private readonly http = inject(HttpClient);

  listar(
    filtros: { targetUser?: number | null; eventType?: string | null },
    offset = 0,
    limit = 50,
  ): Observable<Paginado<EventoAuditoria>> {
    let params = new HttpParams().set('offset', offset).set('limit', limit);
    if (filtros.targetUser) {
      params = params.set('target_user', filtros.targetUser);
    }
    if (filtros.eventType) {
      params = params.set('event_type', filtros.eventType);
    }
    return this.http.get<Paginado<EventoAuditoria>>(apiConfig.routes.accountsAudit, { params });
  }
}
