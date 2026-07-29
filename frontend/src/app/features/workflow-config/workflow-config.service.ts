import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { apiConfig } from '../../core/config/api.config';
import {
  AtualizacaoRascunhoGrupo,
  AtualizacaoRascunhoTemplate,
  GrupoValidacao,
  NovoGrupo,
  NovoTemplate,
  NovaVersaoTemplate,
  PaginaWorkflow,
  SetorWorkflow,
  TemplateChecklist,
  VersaoGrupo,
  VersaoTemplate,
} from './models/workflow-config.models';

@Injectable({ providedIn: 'root' })
export class WorkflowConfigService {
  private readonly http = inject(HttpClient);

  listarSetores(): Observable<PaginaWorkflow<SetorWorkflow>> {
    return this.http.get<PaginaWorkflow<SetorWorkflow>>(
      apiConfig.routes.workflowSectors,
    );
  }

  listarTemplates(query = ''): Observable<PaginaWorkflow<TemplateChecklist>> {
    const params: Record<string, string | number> = { limit: 200 };
    if (query.trim()) {
      params['q'] = query.trim();
    }
    return this.http.get<PaginaWorkflow<TemplateChecklist>>(
      apiConfig.routes.workflowTemplates,
      { params },
    );
  }

  listarGrupos(): Observable<PaginaWorkflow<GrupoValidacao>> {
    return this.http.get<PaginaWorkflow<GrupoValidacao>>(
      apiConfig.routes.workflowGroups,
      { params: { limit: 200 } },
    );
  }

  criarTemplate(payload: NovoTemplate): Observable<TemplateChecklist> {
    return this.http.post<TemplateChecklist>(
      apiConfig.routes.workflowTemplates,
      payload,
    );
  }

  atualizarRascunhoTemplate(
    versionId: number,
    payload: AtualizacaoRascunhoTemplate,
  ): Observable<TemplateChecklist> {
    return this.http.put<TemplateChecklist>(
      `/api/v1/workflow-config/template-versions/${versionId}/`,
      payload,
    );
  }

  criarVersaoTemplate(
    templateId: number,
    payload: NovaVersaoTemplate,
  ): Observable<VersaoTemplate> {
    return this.http.post<VersaoTemplate>(
      `/api/v1/workflow-config/templates/${templateId}/versions/`,
      payload,
    );
  }

  publicarTemplate(
    versionId: number,
    expectedVersion: number,
  ): Observable<VersaoTemplate> {
    return this.http.post<VersaoTemplate>(
      `/api/v1/workflow-config/template-versions/${versionId}/publish/`,
      { expected_version: expectedVersion },
    );
  }

  criarGrupo(payload: NovoGrupo): Observable<GrupoValidacao> {
    return this.http.post<GrupoValidacao>(
      apiConfig.routes.workflowGroups,
      payload,
    );
  }

  atualizarRascunhoGrupo(
    versionId: number,
    payload: AtualizacaoRascunhoGrupo,
  ): Observable<GrupoValidacao> {
    return this.http.put<GrupoValidacao>(
      `/api/v1/workflow-config/group-versions/${versionId}/`,
      payload,
    );
  }

  publicarGrupo(
    versionId: number,
    expectedVersion: number,
  ): Observable<VersaoGrupo> {
    return this.http.post<VersaoGrupo>(
      `/api/v1/workflow-config/group-versions/${versionId}/publish/`,
      { expected_version: expectedVersion },
    );
  }
}
