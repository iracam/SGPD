import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import { ProcessosPage } from './processos';

describe('ProcessosPage', () => {
  let fixture: ComponentFixture<ProcessosPage>;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    });
    fixture = TestBed.createComponent(ProcessosPage);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('mostra os quatro cards e expande tarefas abertas e concluídas', () => {
    const request = httpMock.expectOne(
      (candidate) =>
        candidate.url === '/api/v1/processes/' &&
        candidate.params.get('status') === 'RASCUNHO' &&
        candidate.params.get('limit') === '50',
    );
    request.flush({
      offset: 0,
      limit: 50,
      results: [
        {
          uuid: 'novo',
          status: 'RASCUNHO',
          company_code: 1,
          branch_code: 2,
          employee_type_code: 1,
          employee_registration: 222,
          opened_at: '2026-07-30T14:00:00-03:00',
          completion_at: null,
          planned_termination_date: '2026-08-15',
          due_date: '2026-08-14',
          priority: 'Alta',
          version: 1,
          employee_snapshot: {
            employee_name: 'Rascunho Novo',
            registration: 222,
            branch_legal_name: 'Empresa',
          },
        },
        {
          uuid: 'antigo',
          status: 'RASCUNHO',
          company_code: 1,
          branch_code: 2,
          employee_type_code: 1,
          employee_registration: 111,
          opened_at: '2026-07-29T14:00:00-03:00',
          completion_at: null,
          planned_termination_date: '2026-08-15',
          due_date: '2026-08-14',
          priority: 'Normal',
          version: 1,
          employee_snapshot: {
            employee_name: 'Rascunho Antigo',
            registration: 111,
            branch_legal_name: 'Empresa',
          },
        },
      ],
    });
    httpMock
      .expectOne(
        (candidate) =>
          candidate.url === '/api/v1/processes/' &&
          candidate.params.get('open') === 'true' &&
          candidate.params.get('limit') === '50',
      )
      .flush({
        offset: 0,
        limit: 50,
        results: [
          {
            uuid: 'aberto',
            status: 'INICIADO',
            company_code: 1,
            branch_code: 2,
            employee_type_code: 1,
            employee_registration: 444,
            opened_at: '2026-07-30T12:00:00-03:00',
            completion_at: null,
            planned_termination_date: '2026-08-15',
            due_date: '2026-08-14',
            priority: 'Alta',
            version: 2,
            employee_snapshot: {
              employee_name: 'Processo Em Aberto',
              registration: 444,
              branch_legal_name: 'Empresa',
            },
          },
        ],
      });
    httpMock
      .expectOne(
        (candidate) =>
          candidate.url === '/api/v1/processes/' &&
          candidate.params.get('completed') === 'true' &&
          candidate.params.get('limit') === '50',
      )
      .flush({
        offset: 0,
        limit: 50,
        results: [
          {
            uuid: 'concluido',
            status: 'INICIADO',
            company_code: 1,
            branch_code: 2,
            employee_type_code: 1,
            employee_registration: 333,
            opened_at: '2026-07-29T12:00:00-03:00',
            completion_at: '2026-07-30T15:00:00-03:00',
            planned_termination_date: '2026-08-15',
            due_date: '2026-08-14',
            priority: 'Normal',
            version: 3,
            employee_snapshot: {
              employee_name: 'Processo Concluído',
              registration: 333,
              branch_legal_name: 'Empresa',
            },
          },
        ],
      });
    httpMock
      .expectOne(
        (candidate) =>
          candidate.url === '/api/v1/processes/' &&
          candidate.params.get('status') === 'CANCELADO' &&
          candidate.params.get('limit') === '50',
      )
      .flush({
        offset: 0,
        limit: 50,
        results: [
          {
            uuid: 'cancelado',
            status: 'CANCELADO',
            company_code: 1,
            branch_code: 2,
            employee_type_code: 1,
            employee_registration: 555,
            opened_at: '2026-07-28T12:00:00-03:00',
            completion_at: null,
            planned_termination_date: '2026-08-15',
            due_date: '2026-08-14',
            priority: 'Normal',
            version: 4,
            employee_snapshot: {
              employee_name: 'Processo Cancelado',
              registration: 555,
              branch_legal_name: 'Empresa',
            },
          },
        ],
      });
    fixture.detectChanges();

    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('Abrir processo');
    expect(text).toContain('Rascunhos');
    expect(text).toContain('Em Aberto');
    expect(text).toContain('Concluídos');
    expect(text).toContain('Processo Em Aberto');
    expect(text).toContain('Processo Concluído');
    // Cancelado não está em aberto nem entre os concluídos: sem card próprio,
    // ele sumiria do hub.
    expect(text).toContain('Cancelados');
    expect(text).toContain('Processo Cancelado');
    expect(text.indexOf('Rascunho Novo')).toBeLessThan(text.indexOf('Rascunho Antigo'));

    const processButtons = fixture.nativeElement.querySelectorAll(
      '.processo-lista__item--botao',
    ) as NodeListOf<HTMLButtonElement>;
    const openButton = processButtons[0];
    const concludedButton = processButtons[1];

    openButton.click();
    const openTasksRequest = httpMock.expectOne(
      (candidate) =>
        candidate.url === '/api/v1/processes/aberto/tasks/' &&
        !candidate.params.has('status') &&
        candidate.params.get('limit') === '100',
    );
    openTasksRequest.flush({
      offset: 0,
      limit: 100,
      results: [
        {
          id: 44,
          status: 'EM_ANALISE',
          sector: { id: 7, code: 'DP', name: 'Departamento Pessoal' },
          template: { version_id: 9, code: 'CHECK-DP', version_number: 1 },
          due_at: '2026-08-14T12:00:00-03:00',
          completed_at: null,
        },
      ],
    });
    fixture.detectChanges();

    expect(openButton.getAttribute('aria-expanded')).toBe('true');
    expect(fixture.nativeElement.textContent).toContain('Departamento Pessoal');
    expect(fixture.nativeElement.textContent).toContain('Em análise');

    concludedButton.click();
    const tasksRequest = httpMock.expectOne(
      (candidate) =>
        candidate.url === '/api/v1/processes/concluido/tasks/' &&
        candidate.params.get('status') === 'CONCLUIDA' &&
        candidate.params.get('limit') === '100',
    );
    tasksRequest.flush({
      offset: 0,
      limit: 100,
      results: [
        {
          id: 45,
          status: 'CONCLUIDA',
          sector: { id: 8, code: 'TI', name: 'Tecnologia da Informação' },
          template: { version_id: 10, code: 'CHECK-TI', version_number: 2 },
          due_at: '2026-07-30T12:00:00-03:00',
          completed_at: '2026-07-30T14:30:00-03:00',
        },
      ],
    });
    fixture.detectChanges();

    expect(concludedButton.getAttribute('aria-expanded')).toBe('true');
    expect(fixture.nativeElement.textContent).toContain('Tecnologia da Informação');
  });
});
