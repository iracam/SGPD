import { provideHttpClient } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import { apiConfig } from '../../core/config/api.config';
import { WorkflowConfigPage } from './workflow-config';

describe('WorkflowConfigPage', () => {
  let fixture: ComponentFixture<WorkflowConfigPage>;
  let component: WorkflowConfigPage;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideAnimationsAsync(),
      ],
    });
    fixture = TestBed.createComponent(WorkflowConfigPage);
    component = fixture.componentInstance;
    httpMock = TestBed.inject(HttpTestingController);
    httpMock
      .expectOne(apiConfig.routes.workflowSectors)
      .flush({
        results: [
          { id: 7, code: 'TECNOLOGIA', name: 'Tecnologia', default_due_hours: 24 },
        ],
      });
    httpMock
      .expectOne(
        (request) =>
          request.url === apiConfig.routes.workflowTemplates &&
          request.params.get('limit') === '200',
      )
      .flush({ results: [] });
    httpMock
      .expectOne(
        (request) =>
          request.url === apiConfig.routes.workflowGroups &&
          request.params.get('limit') === '200',
      )
      .flush({ results: [] });
  });

  afterEach(() => httpMock.verify());

  it('cria o primeiro template sem inventar perguntas no cliente', () => {
    component.formularioTemplate.patchValue({
      name: 'Checklist de TI',
      default_due_hours: 12,
    });
    component.formularioTemplate.controls.items.at(0).patchValue({
      code: 'ACESSOS',
      question: 'Os acessos foram encerrados?',
      response_type: 'BOOLEAN',
    });
    component.salvarTemplate();

    const create = httpMock.expectOne(apiConfig.routes.workflowTemplates);
    expect(create.request.method).toBe('POST');
    expect(create.request.body.code).toBeUndefined();
    expect(create.request.body.sector_id).toBeUndefined();
    expect(create.request.body.items).toEqual([
      {
        code: 'ACESSOS',
        question: 'Os acessos foram encerrados?',
        response_type: 'BOOLEAN',
        is_required: true,
        blocks_process: false,
        requires_evidence: false,
        allows_pending: true,
        display_order: 1,
        config: {},
      },
    ]);
    create.flush({ id: 3, code: 3 });

    httpMock.expectOne(apiConfig.routes.workflowSectors).flush({ results: [] });
    httpMock
      .expectOne((request) => request.url === apiConfig.routes.workflowTemplates)
      .flush({ results: [] });
    httpMock
      .expectOne((request) => request.url === apiConfig.routes.workflowGroups)
      .flush({ results: [] });
  });

  it('associa setor e template reutilizável separadamente no grupo', () => {
    component.templates.set([
      {
        id: 3,
        code: 3,
        name: 'Checklist compartilhado',
        description: '',
        is_active: true,
        current_version_id: 12,
        version: 2,
        versions: [
          {
            id: 12,
            version_number: 1,
            status: 'PUBLISHED',
            default_due_hours: 12,
            created_at: '2026-07-29T12:00:00-03:00',
            published_at: '2026-07-29T12:10:00-03:00',
            items: [],
          },
        ],
      },
    ]);
    component.formularioGrupo.patchValue({
      code: 'PADRAO',
      name: 'Desligamento padrão',
    });
    component.formularioGrupo.controls.sectors.at(0).patchValue({
      sector_id: 7,
      template_version_id: 12,
      due_hours_override: 8,
    });

    component.criarGrupo();

    const create = httpMock.expectOne(apiConfig.routes.workflowGroups);
    expect(create.request.method).toBe('POST');
    expect(create.request.body.sectors).toEqual([
      {
        sector_id: 7,
        template_version_id: 12,
        is_required: true,
        blocks_process: true,
        due_hours_override: 8,
        display_order: 1,
      },
    ]);
    create.flush({});

    httpMock.expectOne(apiConfig.routes.workflowSectors).flush({ results: [] });
    httpMock
      .expectOne((request) => request.url === apiConfig.routes.workflowTemplates)
      .flush({ results: [] });
    httpMock
      .expectOne((request) => request.url === apiConfig.routes.workflowGroups)
      .flush({ results: [] });
  });

  it('edita a versão em rascunho com concorrência otimista', () => {
    const template = {
      id: 3,
      code: 3,
      name: 'Checklist de TI',
      description: '',
      is_active: true,
      current_version_id: null,
      version: 1,
      versions: [
        {
          id: 12,
          version_number: 1,
          status: 'DRAFT' as const,
          default_due_hours: 12,
          created_at: '2026-07-29T12:00:00-03:00',
          published_at: null,
          items: [
            {
              id: 21,
              code: 'ACESSOS',
              question: 'Os acessos foram encerrados?',
              response_type: 'BOOLEAN' as const,
              is_required: true,
              blocks_process: true,
              requires_evidence: false,
              allows_pending: true,
              display_order: 1,
              config: {},
            },
          ],
        },
      ],
    };
    component.templates.set([template]);
    component.editarRascunho(template);
    component.formularioTemplate.patchValue({ name: 'Checklist de TI revisado' });
    component.formularioTemplate.controls.items
      .at(0)
      .patchValue({ question: 'Os acessos foram revisados?' });

    component.salvarTemplate();

    const update = httpMock.expectOne(
      '/api/v1/workflow-config/template-versions/12/',
    );
    expect(update.request.method).toBe('PUT');
    expect(update.request.body.expected_version).toBe(1);
    expect(update.request.body.name).toBe('Checklist de TI revisado');
    expect(update.request.body.items[0].display_order).toBe(1);
    update.flush({ ...template, name: 'Checklist de TI revisado', version: 2 });

    httpMock.expectOne(apiConfig.routes.workflowSectors).flush({ results: [] });
    httpMock
      .expectOne((request) => request.url === apiConfig.routes.workflowTemplates)
      .flush({ results: [] });
    httpMock
      .expectOne((request) => request.url === apiConfig.routes.workflowGroups)
      .flush({ results: [] });
  });

  it('clona a versão publicada antes de abrir a edição', () => {
    const template = {
      id: 3,
      code: 3,
      name: 'Checklist publicado',
      description: '',
      is_active: true,
      current_version_id: 12,
      version: 2,
      versions: [
        {
          id: 12,
          version_number: 1,
          status: 'PUBLISHED' as const,
          default_due_hours: 12,
          created_at: '2026-07-29T12:00:00-03:00',
          published_at: '2026-07-29T12:10:00-03:00',
          items: [
            {
              id: 21,
              code: 'ACESSOS',
              question: 'Os acessos foram encerrados?',
              response_type: 'BOOLEAN' as const,
              is_required: true,
              blocks_process: true,
              requires_evidence: false,
              allows_pending: true,
              display_order: 1,
              config: {},
            },
          ],
        },
      ],
    };
    component.templates.set([template]);
    component.templatesVisiveis.set([template]);

    component.criarNovaVersao(template);

    const createVersion = httpMock.expectOne(
      '/api/v1/workflow-config/templates/3/versions/',
    );
    expect(createVersion.request.method).toBe('POST');
    expect(createVersion.request.body.expected_version).toBe(2);
    expect(createVersion.request.body.items[0].id).toBeUndefined();
    createVersion.flush({
      ...template.versions[0],
      id: 13,
      version_number: 2,
      status: 'DRAFT',
      published_at: null,
    });

    expect(component.templateEmEdicao()?.version).toBe(3);
    expect(component.formularioTemplate.controls.name.value).toBe(
      'Checklist publicado',
    );
    expect(component.formularioTemplate.controls.items.at(0).controls.code.value).toBe(
      'ACESSOS',
    );
  });

  it('busca templates pelo nome no servidor', () => {
    component.buscaTemplate.set('tecnologia');

    component.buscarTemplates();

    httpMock
      .expectOne(
        (request) =>
          request.url === apiConfig.routes.workflowTemplates &&
          request.params.get('q') === 'tecnologia',
      )
      .flush({ results: [] });
  });
});
