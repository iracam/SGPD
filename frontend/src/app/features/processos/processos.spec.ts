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

  it('mostra os três cards e lista rascunhos na ordem recebida do backend', () => {
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
    fixture.detectChanges();

    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('Abrir processo');
    expect(text).toContain('Rascunhos');
    expect(text).toContain('Concluídos');
    expect(text).toContain('Processo Concluído');
    expect(text.indexOf('Rascunho Novo')).toBeLessThan(text.indexOf('Rascunho Antigo'));

    const concludedButton = fixture.nativeElement.querySelector(
      '.processo-lista__item--botao',
    ) as HTMLButtonElement;
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
