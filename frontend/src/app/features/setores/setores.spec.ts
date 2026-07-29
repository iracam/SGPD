import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import { apiConfig } from '../../core/config/api.config';
import { Setor } from './models/setores.models';
import { SetoresPage } from './setores';

const SETOR: Setor = {
  id: 4,
  code: 'PATRIMONIO',
  name: 'Patrimônio',
  description: 'Valida bens e equipamentos.',
  is_active: true,
  default_due_hours: 24,
  blocks_process: true,
  allows_amount: true,
  requires_evidence: false,
  escalation_sector: null,
  scopes: [
    {
      scope_type: 'COMPANY',
      company_code: 7,
      branch_code: null,
      scope_key: 'E:7',
    },
  ],
  responsibles: [],
  effective_responsible_count: 0,
  scheduled_responsible_count: 0,
  has_effective_responsible: false,
  version: 1,
  created_at: '2026-07-28T12:00:00-03:00',
  updated_at: '2026-07-28T12:00:00-03:00',
};

describe('SetoresPage', () => {
  let fixture: ComponentFixture<SetoresPage>;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideAnimationsAsync(),
      ],
    });
    fixture = TestBed.createComponent(SetoresPage);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  function responder(setores: Setor[]): void {
    fixture.detectChanges();
    httpMock
      .expectOne(
        (request) =>
          request.url === apiConfig.routes.sectors &&
          request.params.get('limit') === '200',
      )
      .flush({ offset: 0, limit: 200, results: setores });
    httpMock
      .expectOne(
        (request) =>
          request.url === apiConfig.routes.sectorResponsibleCandidates &&
          request.params.get('limit') === '200',
      )
      .flush({
        offset: 0,
        limit: 200,
        results: [
          {
            id: 12,
            username: 'maria.responsavel',
            display_name: 'Maria Responsável',
            email: 'maria.responsavel@example.invalid',
            is_active: true,
          },
        ],
      });
    fixture.detectChanges();
  }

  function responderRecarga(setores: Setor[]): void {
    httpMock
      .expectOne((request) => request.url === apiConfig.routes.sectors)
      .flush({ offset: 0, limit: 200, results: setores });
    httpMock
      .expectOne(
        (request) => request.url === apiConfig.routes.sectorResponsibleCandidates,
      )
      .flush({ offset: 0, limit: 200, results: [] });
  }

  it('renderiza os mesmos setores em cartões e tabela', () => {
    responder([SETOR]);

    expect(fixture.nativeElement.querySelectorAll('.cartao').length).toBe(1);
    expect(fixture.nativeElement.querySelectorAll('.tabela tbody tr').length).toBe(1);
    expect(fixture.nativeElement.textContent).toContain('Empresa 7');
  });

  it('cria setor com escopo e múltiplos responsáveis sem justificativa manual', () => {
    responder([]);
    fixture.componentInstance.abrir();
    const scope = fixture.componentInstance.formulario.controls.scopes.at(0);
    scope.controls.scope_type.setValue('BRANCH');
    fixture.componentInstance.alterarTipoEscopo(0);
    scope.controls.company_code.setValue(7);
    scope.controls.branch_code.setValue(2);
    fixture.componentInstance.formulario.patchValue({
      name: 'Patrimônio',
      description: 'Valida bens e equipamentos.',
      default_due_hours: 24,
      blocks_process: true,
      allows_amount: true,
      requires_evidence: false,
      escalation_sector_id: null,
    });
    fixture.componentInstance.adicionarResponsavel();
    fixture.componentInstance.formulario.controls.responsibles.at(0).patchValue({
      user_id: 12,
      valid_from: '2026-08-01T08:00',
      valid_until: '',
    });
    fixture.detectChanges();

    const saveButton = Array.from(
      fixture.nativeElement.querySelectorAll('button') as NodeListOf<HTMLButtonElement>,
    ).find((button) => button.textContent?.includes('Salvar setor'));
    saveButton?.click();
    fixture.detectChanges();

    const request = httpMock.expectOne(
      (current) =>
        current.url === apiConfig.routes.sectors && current.method === 'POST',
    );
    expect(request.request.body).toEqual({
      name: 'Patrimônio',
      description: 'Valida bens e equipamentos.',
      default_due_hours: 24,
      blocks_process: true,
      allows_amount: true,
      requires_evidence: false,
      escalation_sector_id: null,
      scopes: [
        {
          scope_type: 'BRANCH',
          company_code: 7,
          branch_code: 2,
        },
      ],
      responsibles: [
        {
          user_id: 12,
          valid_from: '2026-08-01T08:00',
          valid_until: null,
        },
      ],
    });
    request.flush(SETOR);
    responderRecarga([SETOR]);
  });

  it('edita por versão sem enviar o código automático', () => {
    responder([SETOR]);
    fixture.componentInstance.abrir(SETOR);
    fixture.componentInstance.formulario.patchValue({
      name: 'Patrimônio corporativo',
    });

    fixture.componentInstance.salvar();

    const request = httpMock.expectOne(
      (current) =>
        current.url === `${apiConfig.routes.sectors}${SETOR.id}/` &&
        current.method === 'PATCH',
    );
    expect(request.request.body.code).toBeUndefined();
    expect(request.request.body.version).toBe(1);
    expect(request.request.body.name).toBe('Patrimônio corporativo');
    request.flush({ ...SETOR, name: 'Patrimônio corporativo', version: 2 });
    responderRecarga([{ ...SETOR, name: 'Patrimônio corporativo', version: 2 }]);
  });

  it('mantém lista vazia e expõe o erro seguro da API', () => {
    fixture.detectChanges();
    httpMock
      .expectOne(
        (request) => request.url === apiConfig.routes.sectorResponsibleCandidates,
      )
      .flush({ offset: 0, limit: 200, results: [] });
    httpMock
      .expectOne((request) => request.url === apiConfig.routes.sectors)
      .flush(
        { code: 'permission_denied', message: 'Usuário sem permissão para manter setores.' },
        { status: 403, statusText: 'Forbidden' },
      );
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain('Usuário sem permissão');
  });
});
