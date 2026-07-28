import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import type { SelectFilterOptions } from 'primeng/types/select';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { apiConfig } from '../../core/config/api.config';
import { ColaboradoresPage } from './colaboradores';
import { ColaboradorSenior } from './models/colaboradores.models';

const COLABORADOR: ColaboradorSenior = {
  company: 1,
  branch: 2,
  legal_name: 'Empresa de Teste',
  employee_type: 1,
  employee_type_description: 'Empregado',
  registration: 123,
  name: 'Pessoa de Teste',
  admission_date: '2020-01-02T00:00:00',
  leave_code: 1,
  leave_description: 'Trabalhando',
  leave_date: null,
  job_structure: 1,
  job_code: 'DEV',
  job_description: 'Desenvolvedor',
  cost_center: '100',
  cost_center_description: null,
  source_updated_at: '2026-07-27T12:00:00',
};

describe('ColaboradoresPage', () => {
  let fixture: ComponentFixture<ColaboradoresPage>;
  let component: ColaboradoresPage;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting(), provideAnimationsAsync()],
    });
    fixture = TestBed.createComponent(ColaboradoresPage);
    component = fixture.componentInstance;
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    vi.useRealTimers();
    httpMock.verify();
  });

  function responderEmpresas(results = [{ company: 1 }]): void {
    const request = httpMock.expectOne(
      (req) =>
        req.url === apiConfig.routes.referenceCompanies &&
        req.params.get('offset') === '0' &&
        req.params.get('limit') === '100',
    );
    request.flush({ offset: 0, limit: 100, results });
  }

  function responderCascataAteColaborador(): void {
    responderEmpresas();
    component.empresa.setValue(1);
    httpMock
      .expectOne(
        (req) =>
          req.url === apiConfig.routes.referenceBranches &&
          req.params.get('company') === '1' &&
          req.params.get('limit') === '100',
      )
      .flush({
        offset: 0,
        limit: 100,
        results: [{ company: 1, branch: 2, legal_name: 'Empresa de Teste' }],
      });
    component.filial.setValue(2);
    httpMock
      .expectOne(
        (req) =>
          req.url === apiConfig.routes.referenceEmployeeTypes &&
          req.params.get('company') === '1' &&
          req.params.get('branch') === '2' &&
          req.params.get('limit') === '100',
      )
      .flush({
        offset: 0,
        limit: 100,
        results: [{ employee_type: 1, description: 'Empregado' }],
      });
    component.tipoColaborador.setValue(1);
  }

  it('consulta os quatro níveis com os limites homologados', () => {
    responderCascataAteColaborador();

    const request = httpMock.expectOne(
      (req) =>
        req.url === apiConfig.routes.referenceEmployees &&
        req.params.get('company') === '1' &&
        req.params.get('branch') === '2' &&
        req.params.get('employee_type') === '1' &&
        req.params.get('offset') === '0' &&
        req.params.get('limit') === '20' &&
        !req.params.has('q'),
    );
    request.flush({ offset: 0, limit: 20, results: [COLABORADOR] });

    expect(component.colaboradores()[0].label).toContain('123 — Pessoa de Teste');
  });

  it('limpa todos os níveis descendentes ao trocar a empresa', () => {
    responderCascataAteColaborador();
    httpMock
      .expectOne((req) => req.url === apiConfig.routes.referenceEmployees)
      .flush({ offset: 0, limit: 20, results: [COLABORADOR] });
    component.colaborador.setValue(123);

    component.empresa.setValue(2);

    expect(component.filial.value).toBeNull();
    expect(component.tipoColaborador.value).toBeNull();
    expect(component.colaborador.value).toBeNull();
    expect(component.filiais()).toEqual([]);
    expect(component.tiposColaborador()).toEqual([]);
    expect(component.colaboradores()).toEqual([]);
    httpMock
      .expectOne(
        (req) =>
          req.url === apiConfig.routes.referenceBranches &&
          req.params.get('company') === '2',
      )
      .flush({ offset: 0, limit: 100, results: [] });
  });

  it('cancela a consulta anterior quando a empresa muda antes da resposta', () => {
    responderEmpresas([{ company: 1 }, { company: 2 }]);
    component.empresa.setValue(1);
    const antiga = httpMock.expectOne(
      (req) =>
        req.url === apiConfig.routes.referenceBranches &&
        req.params.get('company') === '1',
    );

    component.empresa.setValue(2);

    expect(antiga.cancelled).toBe(true);
    httpMock
      .expectOne(
        (req) =>
          req.url === apiConfig.routes.referenceBranches &&
          req.params.get('company') === '2',
      )
      .flush({ offset: 0, limit: 100, results: [] });
  });

  it('faz busca remota pelo filtro após debounce e limita a cem caracteres', () => {
    vi.useFakeTimers();
    responderCascataAteColaborador();
    httpMock
      .expectOne((req) => req.url === apiConfig.routes.referenceEmployees)
      .flush({ offset: 0, limit: 20, results: [] });
    const input = document.createElement('input');
    input.value = `  ${'Pessoa'.repeat(20)}  `;
    const filter = vi.fn();

    component.filtrarColaboradores(
      { target: input } as unknown as Event,
      { filter } satisfies SelectFilterOptions,
    );
    vi.advanceTimersByTime(399);
    httpMock.expectNone((req) => req.url === apiConfig.routes.referenceEmployees);
    vi.advanceTimersByTime(1);

    const request = httpMock.expectOne(
      (req) =>
        req.url === apiConfig.routes.referenceEmployees &&
        req.params.get('q') === input.value.trim(),
    );
    expect(input.value.length).toBe(100);
    expect(filter).toHaveBeenCalledOnce();
    request.flush({ offset: 0, limit: 20, results: [] });
  });

  it('cancela imediatamente a consulta de colaborador quando o filtro muda', () => {
    vi.useFakeTimers();
    responderCascataAteColaborador();
    const antiga = httpMock.expectOne(
      (req) =>
        req.url === apiConfig.routes.referenceEmployees &&
        !req.params.has('q'),
    );
    const input = document.createElement('input');
    input.value = 'Pessoa';

    component.filtrarColaboradores(
      { target: input } as unknown as Event,
      { filter: vi.fn() } satisfies SelectFilterOptions,
    );

    expect(antiga.cancelled).toBe(true);
    vi.advanceTimersByTime(400);
    httpMock
      .expectOne(
        (req) =>
          req.url === apiConfig.routes.referenceEmployees &&
          req.params.get('q') === 'Pessoa',
      )
      .flush({ offset: 0, limit: 20, results: [COLABORADOR] });
  });

  it.each([
    [403, 'permission_denied', 'Usuário sem permissão para este escopo cadastral.'],
    [502, 'senior_contract_error', 'Resposta inválida da fonte cadastral.'],
    [503, 'senior_unavailable', 'Senior HCM indisponível para consulta.'],
  ])('exibe erro seguro da API para resposta %i', (status, code, message) => {
    httpMock
      .expectOne((req) => req.url === apiConfig.routes.referenceCompanies)
      .flush(
        { code, message, oracle_detail: 'ORA-00000 dado interno' },
        { status, statusText: 'Erro esperado' },
      );
    fixture.detectChanges();

    const content = fixture.nativeElement.textContent as string;
    expect(content).toContain(message);
    expect(content).not.toContain('ORA-00000');
  });

  it('não projeta CPF e apresenta somente os dados autorizados do selecionado', () => {
    responderCascataAteColaborador();
    httpMock
      .expectOne((req) => req.url === apiConfig.routes.referenceEmployees)
      .flush({
        offset: 0,
        limit: 20,
        results: [
          {
            ...COLABORADOR,
            cpf: '123.456.789-00',
            masked_cpf: '***.456.***-**',
          },
        ],
      });
    component.colaborador.setValue(123);
    fixture.detectChanges();

    const content = fixture.nativeElement.textContent as string;
    expect(content).toContain('Pessoa de Teste');
    expect(content).toContain('Desenvolvedor');
    expect(content).not.toContain('123.456.789-00');
    expect(content).not.toContain('***.456.***-**');
    expect(content.toLowerCase()).not.toContain('cpf');
  });
});
