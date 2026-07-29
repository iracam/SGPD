import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { apiConfig } from '../../core/config/api.config';
import { Paginado } from '../usuarios/models/usuarios.models';
import { EdicaoSetor, NovoSetor, Setor } from './models/setores.models';

@Injectable({ providedIn: 'root' })
export class SetoresService {
  private readonly http = inject(HttpClient);
  private readonly base = apiConfig.routes.sectors;

  listar(): Observable<Paginado<Setor>> {
    return this.http.get<Paginado<Setor>>(this.base, { params: { limit: 200 } });
  }

  criar(payload: NovoSetor): Observable<Setor> {
    return this.http.post<Setor>(this.base, payload);
  }

  atualizar(id: number, payload: EdicaoSetor): Observable<Setor> {
    return this.http.patch<Setor>(`${this.base}${id}/`, payload);
  }
}
