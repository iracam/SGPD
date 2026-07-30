import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { apiConfig } from '../../core/config/api.config';
import {
  ColaboradorSenior,
  EmpresaSenior,
  FilialSenior,
  NovaAberturaProcesso,
  PaginaSenior,
  ProcessoAberto,
  TipoColaboradorSenior,
} from './models/colaboradores.models';

@Injectable({ providedIn: 'root' })
export class ColaboradoresService {
  private readonly http = inject(HttpClient);

  listarEmpresas(): Observable<PaginaSenior<EmpresaSenior>> {
    const params = new HttpParams().set('offset', 0).set('limit', 100);
    return this.http.get<PaginaSenior<EmpresaSenior>>(apiConfig.routes.referenceCompanies, {
      params,
    });
  }

  listarFiliais(company: number): Observable<PaginaSenior<FilialSenior>> {
    const params = new HttpParams()
      .set('company', company)
      .set('offset', 0)
      .set('limit', 100);
    return this.http.get<PaginaSenior<FilialSenior>>(apiConfig.routes.referenceBranches, {
      params,
    });
  }

  listarTipos(
    company: number,
    branch: number,
  ): Observable<PaginaSenior<TipoColaboradorSenior>> {
    const params = new HttpParams()
      .set('company', company)
      .set('branch', branch)
      .set('offset', 0)
      .set('limit', 100);
    return this.http.get<PaginaSenior<TipoColaboradorSenior>>(
      apiConfig.routes.referenceEmployeeTypes,
      { params },
    );
  }

  listarColaboradores(
    company: number,
    branch: number,
    employeeType: number,
    query: string,
  ): Observable<PaginaSenior<ColaboradorSenior>> {
    let params = new HttpParams()
      .set('company', company)
      .set('branch', branch)
      .set('employee_type', employeeType)
      .set('offset', 0)
      .set('limit', 20);
    if (query) {
      params = params.set('q', query);
    }
    return this.http.get<PaginaSenior<ColaboradorSenior>>(
      apiConfig.routes.referenceEmployees,
      { params },
    );
  }

  abrirProcesso(payload: NovaAberturaProcesso): Observable<ProcessoAberto> {
    return this.http.post<ProcessoAberto>(apiConfig.routes.processes, payload);
  }
}
