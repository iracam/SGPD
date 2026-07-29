import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { apiConfig } from '../../core/config/api.config';
import { Paginado } from '../usuarios/models/usuarios.models';
import {
  CandidatoResponsavel,
  EdicaoResponsabilidadeSetor,
  NovaResponsabilidadeSetor,
  ResponsabilidadeSetor,
  RevogacaoResponsabilidadeSetor,
} from './models/responsaveis.models';

@Injectable({ providedIn: 'root' })
export class ResponsaveisService {
  private readonly http = inject(HttpClient);
  private readonly base = apiConfig.routes.sectorResponsibilities;

  listar(): Observable<Paginado<ResponsabilidadeSetor>> {
    return this.http.get<Paginado<ResponsabilidadeSetor>>(this.base, {
      params: { limit: 200 },
    });
  }

  listarCandidatos(): Observable<Paginado<CandidatoResponsavel>> {
    return this.http.get<Paginado<CandidatoResponsavel>>(
      apiConfig.routes.sectorResponsibilityCandidates,
      { params: { limit: 200 } },
    );
  }

  associar(payload: NovaResponsabilidadeSetor): Observable<ResponsabilidadeSetor> {
    return this.http.post<ResponsabilidadeSetor>(this.base, payload);
  }

  atualizar(
    id: number,
    payload: EdicaoResponsabilidadeSetor,
  ): Observable<ResponsabilidadeSetor> {
    return this.http.patch<ResponsabilidadeSetor>(`${this.base}${id}/`, payload);
  }

  revogar(
    id: number,
    payload: RevogacaoResponsabilidadeSetor,
  ): Observable<ResponsabilidadeSetor> {
    return this.http.post<ResponsabilidadeSetor>(
      `${this.base}${id}/revoke/`,
      payload,
    );
  }
}
