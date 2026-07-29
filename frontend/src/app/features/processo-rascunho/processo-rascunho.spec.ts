import { provideHttpClient } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { ActivatedRoute } from '@angular/router';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import { ProcessoRascunhoPage } from './processo-rascunho';
import { ContextoRascunho } from './models/processo-rascunho.models';

const UUID = '3ca25d06-ca5d-4a49-a9df-d42d74a1d6b2';

function contexto(status: 'RASCUNHO' | 'INICIADO' = 'RASCUNHO'): ContextoRascunho {
  return {
    process: {
      uuid: UUID,
      status,
      company_code: 1,
      branch_code: 2,
      employee_registration: 123,
      opened_at: '2026-07-29T12:00:00-03:00',
      started_at: status === 'INICIADO' ? '2026-07-29T13:00:00-03:00' : null,
      due_date: '2026-08-14',
      version: status === 'INICIADO' ? 3 : 2,
      employee_snapshot: { employee_name: 'Pessoa de Teste', registration: 123 },
    },
    selection: {
      group_version_ids: [10],
      groups: [{ version_id: 10, code: 'PADRAO', name: 'Padrão', version_number: 1 }],
      overrides: [],
      resolved_sectors: [
        {
          sector_id: 7,
          code: 'TECNOLOGIA',
          name: 'Tecnologia',
          template_version_id: 20,
          template_code: 'TPL_TI',
          template_version_number: 1,
          is_required: true,
          blocks_process: true,
          sla_hours: 12,
          source: 'GROUP',
        },
      ],
      blockers: [],
    },
    available_groups: [
      {
        version_id: 10,
        group_id: 1,
        code: 'PADRAO',
        name: 'Padrão',
        description: '',
        version_number: 1,
        sectors: [],
      },
      {
        version_id: 11,
        group_id: 2,
        code: 'CRITICO',
        name: 'Crítico',
        description: '',
        version_number: 1,
        sectors: [],
      },
    ],
    tasks: [],
  };
}

describe('ProcessoRascunhoPage', () => {
  let fixture: ComponentFixture<ProcessoRascunhoPage>;
  let component: ProcessoRascunhoPage;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideAnimationsAsync(),
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { paramMap: { get: () => UUID } } },
        },
      ],
    });
    fixture = TestBed.createComponent(ProcessoRascunhoPage);
    component = fixture.componentInstance;
    httpMock = TestBed.inject(HttpTestingController);
    httpMock
      .expectOne(`/api/v1/processes/${UUID}/draft/`)
      .flush(contexto());
  });

  afterEach(() => httpMock.verify());

  it('salva a seleção com a versão otimista antes do início', () => {
    component.formulario.controls.group_version_ids.setValue([10, 11]);
    component.salvarSelecao();

    const request = httpMock.expectOne(
      `/api/v1/processes/${UUID}/draft/selection/`,
    );
    expect(request.request.method).toBe('PUT');
    expect(request.request.body).toEqual({
      expected_version: 2,
      group_version_ids: [10, 11],
      overrides: [],
    });
    const atualizado = contexto();
    atualizado.process.version = 3;
    atualizado.selection.group_version_ids = [10, 11];
    request.flush(atualizado);

    expect(component.selecaoAlterada()).toBe(false);
    expect(component.contexto()?.process.version).toBe(3);
  });

  it('envia chave idempotente e projeta as tarefas retornadas', () => {
    component.iniciar();

    const request = httpMock.expectOne(`/api/v1/processes/${UUID}/start/`);
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual({ expected_version: 2 });
    expect(request.request.headers.get('Idempotency-Key')).toBeTruthy();
    const iniciado = contexto('INICIADO');
    iniciado.tasks = [
      {
        id: 1,
        status: 'PENDENTE',
        sector: { id: 7, code: 'TECNOLOGIA', name: 'Tecnologia' },
        template: { version_id: 20, code: 'TPL_TI', version_number: 1 },
        is_required: true,
        blocks_process: true,
        sla_hours: 12,
        due_at: '2026-07-30T01:00:00-03:00',
        started_at: '2026-07-29T13:00:00-03:00',
        checklist_item_count: 1,
        version: 1,
      },
    ];
    request.flush(iniciado);

    expect(component.iniciado()).toBe(true);
    expect(component.contexto()?.tasks).toHaveLength(1);
  });
});
