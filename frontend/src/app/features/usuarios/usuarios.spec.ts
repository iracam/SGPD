import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { provideRouter } from '@angular/router';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import { apiConfig } from '../../core/config/api.config';
import { Usuario } from './models/usuarios.models';
import { UsuariosPage } from './usuarios';

const USUARIO: Usuario = {
  id: 1,
  username: 'api.comum',
  email: 'api.comum@example.invalid',
  first_name: 'Api',
  last_name: 'Comum',
  display_name: 'Api Comum',
  must_change_password: false,
  is_superuser: false,
  is_active: true,
  version: 1,
  date_joined: null,
  last_login: null,
  ad_identifier: null,
  ad_username: null,
  ad_linked_at: null,
  ad_linked_by: null,
};

describe('UsuariosPage', () => {
  let fixture: ComponentFixture<UsuariosPage>;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        provideAnimationsAsync(),
      ],
    });
    fixture = TestBed.createComponent(UsuariosPage);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  function responder(usuarios: Usuario[]): void {
    fixture.detectChanges();
    const req = httpMock.expectOne((r) => r.url === apiConfig.routes.accountsUsers);
    req.flush({ offset: 0, limit: 50, results: usuarios });
    fixture.detectChanges();
  }

  it('renderiza os mesmos dados como cartão e como linha de tabela', () => {
    responder([USUARIO]);

    // A ADR-028 exige as duas representações; a visibilidade é decidida por CSS.
    expect(fixture.nativeElement.querySelectorAll('.cartao').length).toBe(1);
    expect(fixture.nativeElement.querySelectorAll('.tabela tbody tr').length).toBe(1);
  });

  it('anuncia lista vazia em vez de deixar a tela em branco', () => {
    responder([]);

    expect(fixture.nativeElement.querySelector('.vazio')).not.toBeNull();
  });

  it('marca senha temporária e conta inativa', () => {
    responder([{ ...USUARIO, must_change_password: true, is_active: false }]);

    const selos = fixture.nativeElement.textContent as string;
    expect(selos).toContain('Senha temporária');
    expect(selos).toContain('Inativo');
  });

  it('exibe a mensagem do envelope quando a listagem falha', () => {
    fixture.detectChanges();
    httpMock
      .expectOne((r) => r.url === apiConfig.routes.accountsUsers)
      .flush(
        { code: 'permission_denied', message: 'Usuário sem permissão para esta operação.' },
        { status: 403, statusText: 'Forbidden' },
      );
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain('Usuário sem permissão');
  });
});
