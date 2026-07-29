import { provideHttpClient } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import { apiConfig } from '../../core/config/api.config';
import { Setor } from '../setores/models/setores.models';
import {
  CandidatoResponsavel,
  ResponsabilidadeSetor,
} from './models/responsaveis.models';
import { ResponsaveisPage } from './responsaveis';

const SETOR: Setor = {
  id: 4,
  code: 'TI',
  name: 'Tecnologia da Informação',
  description: 'Valida acessos e equipamentos.',
  is_active: true,
  default_due_hours: 24,
  blocks_process: true,
  allows_amount: false,
  requires_evidence: false,
  escalation_sector: null,
  scopes: [
    {
      scope_type: 'GLOBAL',
      company_code: null,
      branch_code: null,
      scope_key: '*',
    },
  ],
  version: 1,
  created_at: '2026-07-29T08:00:00-03:00',
  updated_at: '2026-07-29T08:00:00-03:00',
};

const CANDIDATO: CandidatoResponsavel = {
  id: 9,
  username: 'maria.responsavel',
  display_name: 'Maria Responsável',
  email: 'maria.responsavel@example.invalid',
  role_scopes: [
    {
      scope_type: 'GLOBAL',
      company_code: null,
      branch_code: null,
      scope_key: '*',
      valid_from: '2026-07-28T09:00:00-03:00',
      valid_until: null,
    },
  ],
};

const RESPONSABILIDADE: ResponsabilidadeSetor = {
  id: 12,
  sector: {
    id: SETOR.id,
    code: SETOR.code,
    name: SETOR.name,
    is_active: true,
  },
  user: {
    id: CANDIDATO.id,
    username: CANDIDATO.username,
    display_name: CANDIDATO.display_name,
    email: CANDIDATO.email,
    is_active: true,
  },
  scope_type: 'GLOBAL',
  company_code: null,
  branch_code: null,
  scope_key: '*',
  valid_from: '2026-07-29T09:00:00-03:00',
  valid_until: null,
  is_active: true,
  is_effective: true,
  assigned_at: '2026-07-29T09:00:00-03:00',
  updated_at: '2026-07-29T09:00:00-03:00',
  revoked_at: null,
  version: 1,
};

describe('ResponsaveisPage', () => {
  let fixture: ComponentFixture<ResponsaveisPage>;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideAnimationsAsync(),
      ],
    });
    fixture = TestBed.createComponent(ResponsaveisPage);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  function responderCarga(
    responsibilities: ResponsabilidadeSetor[] = [RESPONSABILIDADE],
  ): void {
    fixture.detectChanges();
    httpMock
      .expectOne(
        (request) =>
          request.url === apiConfig.routes.sectorResponsibilities &&
          request.params.get('limit') === '200',
      )
      .flush({ offset: 0, limit: 200, results: responsibilities });
    httpMock
      .expectOne(
        (request) =>
          request.url === apiConfig.routes.sectorResponsibilityCandidates &&
          request.params.get('limit') === '200',
      )
      .flush({ offset: 0, limit: 200, results: [CANDIDATO] });
    httpMock
      .expectOne(
        (request) =>
          request.url === apiConfig.routes.sectors &&
          request.params.get('limit') === '200',
      )
      .flush({ offset: 0, limit: 200, results: [SETOR] });
    fixture.detectChanges();
  }

  function responderRecarga(
    responsibilities: ResponsabilidadeSetor[] = [RESPONSABILIDADE],
  ): void {
    httpMock
      .expectOne((request) => request.url === apiConfig.routes.sectorResponsibilities)
      .flush({ offset: 0, limit: 200, results: responsibilities });
    httpMock
      .expectOne(
        (request) => request.url === apiConfig.routes.sectorResponsibilityCandidates,
      )
      .flush({ offset: 0, limit: 200, results: [CANDIDATO] });
    httpMock
      .expectOne((request) => request.url === apiConfig.routes.sectors)
      .flush({ offset: 0, limit: 200, results: [SETOR] });
  }

  it('renderiza as mesmas responsabilidades em cartões e tabela', () => {
    responderCarga();

    expect(fixture.nativeElement.querySelectorAll('.cartao').length).toBe(1);
    expect(fixture.nativeElement.querySelectorAll('.tabela tbody tr').length).toBe(1);
    expect(fixture.nativeElement.textContent).toContain('Maria Responsável');
    expect(fixture.nativeElement.textContent).toContain('Todas as empresas');
  });

  it('associa usuário, setor, escopo e validade explicitamente', () => {
    responderCarga([]);
    fixture.componentInstance.abrir();
    fixture.componentInstance.formulario.patchValue({
      sector_id: SETOR.id,
      user_id: CANDIDATO.id,
      scope_type: 'GLOBAL',
      valid_from: '2026-07-29T09:00',
      valid_until: null,
      reason: 'Associação funcional homologada.',
    });

    fixture.componentInstance.salvar();

    const request = httpMock.expectOne(
      (current) =>
        current.url === apiConfig.routes.sectorResponsibilities &&
        current.method === 'POST',
    );
    expect(request.request.body).toEqual({
      sector_id: SETOR.id,
      user_id: CANDIDATO.id,
      scope_type: 'GLOBAL',
      company_code: null,
      branch_code: null,
      valid_from: '2026-07-29T09:00',
      valid_until: null,
      reason: 'Associação funcional homologada.',
    });
    request.flush(RESPONSABILIDADE);
    responderRecarga();
  });

  it('edita somente a validade usando a versão recebida', () => {
    responderCarga();
    fixture.componentInstance.abrir(RESPONSABILIDADE);
    fixture.componentInstance.formulario.patchValue({
      valid_until: '2026-08-29T18:00',
      reason: 'Validade revisada.',
    });

    fixture.componentInstance.salvar();

    const request = httpMock.expectOne(
      (current) =>
        current.url ===
          `${apiConfig.routes.sectorResponsibilities}${RESPONSABILIDADE.id}/` &&
        current.method === 'PATCH',
    );
    expect(request.request.body.version).toBe(1);
    expect(request.request.body.valid_until).toBe('2026-08-29T18:00');
    expect(request.request.body.sector_id).toBeUndefined();
    request.flush({
      ...RESPONSABILIDADE,
      valid_until: '2026-08-29T18:00:00-03:00',
      version: 2,
    });
    responderRecarga([
      {
        ...RESPONSABILIDADE,
        valid_until: '2026-08-29T18:00:00-03:00',
        version: 2,
      },
    ]);
  });

  it('revoga logicamente com justificativa e versão', () => {
    responderCarga();
    fixture.componentInstance.abrirRevogacao(RESPONSABILIDADE);
    fixture.componentInstance.formularioRevogacao.patchValue({
      reason: 'Responsável substituído.',
    });

    fixture.componentInstance.revogar();

    const request = httpMock.expectOne(
      (current) =>
        current.url ===
          `${apiConfig.routes.sectorResponsibilities}${RESPONSABILIDADE.id}/revoke/` &&
        current.method === 'POST',
    );
    expect(request.request.body).toEqual({
      version: 1,
      reason: 'Responsável substituído.',
    });
    request.flush({
      ...RESPONSABILIDADE,
      is_active: false,
      is_effective: false,
      version: 2,
    });
    responderRecarga([
      {
        ...RESPONSABILIDADE,
        is_active: false,
        is_effective: false,
        version: 2,
      },
    ]);
  });
});
