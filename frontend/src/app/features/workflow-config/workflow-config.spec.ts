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
      code: 'TPL_TI',
      sector_id: 7,
      name: 'Checklist de TI',
      default_due_hours: 12,
    });
    component.formularioTemplate.controls.items.at(0).patchValue({
      code: 'ACESSOS',
      question: 'Os acessos foram encerrados?',
      response_type: 'BOOLEAN',
    });
    component.criarTemplate();

    const create = httpMock.expectOne(apiConfig.routes.workflowTemplates);
    expect(create.request.method).toBe('POST');
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
    create.flush({});

    httpMock.expectOne(apiConfig.routes.workflowSectors).flush({ results: [] });
    httpMock
      .expectOne((request) => request.url === apiConfig.routes.workflowTemplates)
      .flush({ results: [] });
    httpMock
      .expectOne((request) => request.url === apiConfig.routes.workflowGroups)
      .flush({ results: [] });
  });
});
