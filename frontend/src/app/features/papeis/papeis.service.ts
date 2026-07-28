import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { apiConfig } from '../../core/config/api.config';
import { Paginado } from '../usuarios/models/usuarios.models';
import { EdicaoPapel, NovoPapel, Papel, Permissao } from './models/papeis.models';

@Injectable({ providedIn: 'root' })
export class PapeisService {
  private readonly http = inject(HttpClient);
  private readonly base = apiConfig.routes.accountsRoles;

  listar(): Observable<Paginado<Papel>> {
    return this.http.get<Paginado<Papel>>(this.base, { params: { limit: 200 } });
  }

  permissoes(): Observable<{ results: Permissao[] }> {
    return this.http.get<{ results: Permissao[] }>(apiConfig.routes.accountsPermissions);
  }

  criar(payload: NovoPapel): Observable<Papel> {
    return this.http.post<Papel>(this.base, payload);
  }

  atualizar(id: number, payload: EdicaoPapel): Observable<Papel> {
    return this.http.patch<Papel>(`${this.base}${id}/`, payload);
  }
}
