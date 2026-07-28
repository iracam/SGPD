import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { apiConfig } from '../../core/config/api.config';
import {
  LdapCertificateValidationResult,
  LdapConfiguration,
  LdapConfigurationPayload,
  LdapConnectionTestResult,
  LdapDirectoryGroup,
  LdapDirectoryPage,
  LdapValidationResult,
} from './models/configuracoes.models';

@Injectable({ providedIn: 'root' })
export class ConfiguracoesService {
  private readonly http = inject(HttpClient);

  carregarLdap(): Observable<LdapConfiguration> {
    return this.http.get<LdapConfiguration>(apiConfig.routes.settingsLdap);
  }

  salvarLdap(payload: LdapConfigurationPayload): Observable<LdapConfiguration> {
    return this.http.put<LdapConfiguration>(apiConfig.routes.settingsLdap, payload);
  }

  validarLdap(payload: LdapConfigurationPayload): Observable<LdapValidationResult> {
    return this.http.post<LdapValidationResult>(
      apiConfig.routes.settingsLdapValidate,
      payload,
    );
  }

  enviarCertificado(
    version: number,
    certificate: File,
  ): Observable<LdapConfiguration> {
    const formData = new FormData();
    formData.append('version', String(version));
    formData.append('certificate', certificate, certificate.name);
    return this.http.post<LdapConfiguration>(
      apiConfig.routes.settingsLdapCertificate,
      formData,
    );
  }

  validarCertificado(): Observable<LdapCertificateValidationResult> {
    return this.http.post<LdapCertificateValidationResult>(
      apiConfig.routes.settingsLdapCertificateValidate,
      {},
    );
  }

  testarConexao(): Observable<LdapConnectionTestResult> {
    return this.http.post<LdapConnectionTestResult>(
      apiConfig.routes.settingsLdapConnectionTest,
      {},
    );
  }

  buscarGruposLdap(
    busca: string,
    limit = 50,
  ): Observable<LdapDirectoryPage<LdapDirectoryGroup>> {
    const params = new HttpParams().set('q', busca.trim()).set('limit', limit);
    return this.http.get<LdapDirectoryPage<LdapDirectoryGroup>>(
      apiConfig.routes.accountsDirectoryGroups,
      { params },
    );
  }
}
