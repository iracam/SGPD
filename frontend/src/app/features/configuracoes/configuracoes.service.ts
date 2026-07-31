import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { apiConfig } from '../../core/config/api.config';
import {
  EmailConfiguration,
  EmailConfigurationPayload,
  EmailDeliveryTestResult,
  EmailValidationResult,
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

  carregarEmail(): Observable<EmailConfiguration> {
    return this.http.get<EmailConfiguration>(apiConfig.routes.settingsEmail);
  }

  salvarEmail(payload: EmailConfigurationPayload): Observable<EmailConfiguration> {
    return this.http.put<EmailConfiguration>(apiConfig.routes.settingsEmail, payload);
  }

  validarEmail(payload: EmailConfigurationPayload): Observable<EmailValidationResult> {
    return this.http.post<EmailValidationResult>(
      apiConfig.routes.settingsEmailValidate,
      payload,
    );
  }

  testarEnvioEmail(): Observable<EmailDeliveryTestResult> {
    return this.http.post<EmailDeliveryTestResult>(
      apiConfig.routes.settingsEmailDeliveryTest,
      {},
    );
  }

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
