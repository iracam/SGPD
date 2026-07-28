import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { apiConfig } from '../../core/config/api.config';
import {
  EdicaoUsuario,
  NovaAtribuicao,
  NovoUsuario,
  Paginado,
  RedefinicaoSenha,
  Usuario,
  UsuarioDetalhe,
  VinculoAd,
} from './models/usuarios.models';

@Injectable({ providedIn: 'root' })
export class UsuariosService {
  private readonly http = inject(HttpClient);
  private readonly base = apiConfig.routes.accountsUsers;

  listar(busca: string, offset = 0, limit = 50): Observable<Paginado<Usuario>> {
    let params = new HttpParams().set('offset', offset).set('limit', limit);
    if (busca.trim()) {
      params = params.set('q', busca.trim());
    }
    return this.http.get<Paginado<Usuario>>(this.base, { params });
  }

  detalhe(id: number): Observable<UsuarioDetalhe> {
    return this.http.get<UsuarioDetalhe>(`${this.base}${id}/`);
  }

  criar(payload: NovoUsuario): Observable<Usuario> {
    return this.http.post<Usuario>(this.base, payload);
  }

  atualizar(id: number, payload: EdicaoUsuario): Observable<UsuarioDetalhe> {
    return this.http.patch<UsuarioDetalhe>(`${this.base}${id}/`, payload);
  }

  redefinirSenha(id: number, payload: RedefinicaoSenha): Observable<UsuarioDetalhe> {
    return this.http.post<UsuarioDetalhe>(`${this.base}${id}/reset-password/`, payload);
  }

  atribuirPapel(id: number, payload: NovaAtribuicao): Observable<unknown> {
    return this.http.post(`${this.base}${id}/roles/`, payload);
  }

  revogarAtribuicao(atribuicaoId: number, reason: string): Observable<unknown> {
    return this.http.post(
      `${apiConfig.routes.accountsRoleAssignments}${atribuicaoId}/revoke/`,
      { reason },
    );
  }

  vincularAd(id: number, payload: VinculoAd): Observable<UsuarioDetalhe> {
    return this.http.post<UsuarioDetalhe>(`${this.base}${id}/ad-link/`, payload);
  }

  desvincularAd(id: number, version: number, reason: string): Observable<UsuarioDetalhe> {
    return this.http.post<UsuarioDetalhe>(`${this.base}${id}/ad-unlink/`, { version, reason });
  }
}
