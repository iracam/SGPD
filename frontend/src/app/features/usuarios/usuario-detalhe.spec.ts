import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { of, throwError } from 'rxjs';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { AuthService } from '../../core/auth/auth.service';
import { PapeisService } from '../papeis/papeis.service';
import { UsuarioDetalhe } from './models/usuarios.models';
import { UsuarioDetalhePage } from './usuario-detalhe';
import { UsuariosService } from './usuarios.service';

const LINKED_USER: UsuarioDetalhe = {
  id: 10,
  username: 'maria.silva',
  email: 'maria.silva@example.internal',
  first_name: 'Maria',
  last_name: 'Silva',
  display_name: 'Maria Silva',
  must_change_password: false,
  is_superuser: false,
  is_active: true,
  version: 1,
  date_joined: null,
  last_login: null,
  ad_identifier: '0899b887-704b-4c59-ae09-3a678a4e02a1',
  ad_username: 'maria.silva',
  ad_linked_at: '2026-07-28T18:00:00Z',
  ad_linked_by: 'admin',
  ad_authentication_enabled: true,
  local_password_allowed: false,
  role_assignments: [],
};

describe('UsuarioDetalhePage', () => {
  let fixture: ComponentFixture<UsuarioDetalhePage>;
  let target: UsuarioDetalhe;

  beforeEach(() => {
    target = LINKED_USER;
    TestBed.configureTestingModule({
      providers: [
        provideAnimationsAsync(),
        {
          provide: UsuariosService,
          useValue: {
            detalhe: vi.fn(() => of(target)),
            atribuirPapel: vi.fn(() => of({})),
          },
        },
        {
          provide: PapeisService,
          useValue: {
            listar: vi.fn(() => of({ offset: 0, limit: 50, results: [] })),
          },
        },
        {
          provide: AuthService,
          useValue: {
            canView: vi.fn(() => true),
          },
        },
      ],
    });
  });

  async function render(): Promise<void> {
    fixture = TestBed.createComponent(UsuarioDetalhePage);
    fixture.componentRef.setInput('id', String(target.id));
    await Promise.resolve();
    fixture.detectChanges();
  }

  it('bloqueia redefinição local quando a conta vinculada usa autenticação AD', async () => {
    await render();

    const resetButton = Array.from(
      fixture.nativeElement.querySelectorAll('button') as NodeListOf<HTMLButtonElement>,
    ).find((button) => button.textContent?.includes('Redefinir senha'));
    expect(resetButton?.disabled).toBe(true);
    expect(fixture.nativeElement.textContent).toContain(
      'Autenticação AD ativa: a senha local está bloqueada',
    );

    fixture.componentInstance.abrir('senha');
    expect(fixture.componentInstance.acao()).toBeNull();
  });

  it('mantém a redefinição disponível para a contingência de superusuário', async () => {
    target = {
      ...LINKED_USER,
      is_superuser: true,
      local_password_allowed: true,
    };
    await render();

    const resetButton = Array.from(
      fixture.nativeElement.querySelectorAll('button') as NodeListOf<HTMLButtonElement>,
    ).find((button) => button.textContent?.includes('Redefinir senha'));
    expect(resetButton?.disabled).toBe(false);
    expect(fixture.nativeElement.textContent).toContain(
      'Senha local disponível somente pela contingência',
    );

    fixture.componentInstance.abrir('senha');
    expect(fixture.componentInstance.acao()).toBe('senha');
  });

  it('atribui papel sem solicitar ou enviar justificativa manual', async () => {
    await render();
    fixture.componentInstance.abrir('papel');
    fixture.componentInstance.formPapel.setValue({
      role_id: 7,
      scope_type: 'COMPANY',
      company_code: 1,
      branch_code: null,
    });
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('label[for="p_reason"]')).toBeNull();

    const confirmButton = Array.from(
      fixture.nativeElement.querySelectorAll('button') as NodeListOf<HTMLButtonElement>,
    ).find((button) => button.textContent?.includes('Confirmar'));
    confirmButton?.click();
    fixture.detectChanges();

    const service = TestBed.inject(UsuariosService);
    expect(service.atribuirPapel).toHaveBeenCalledWith(target.id, {
      role_id: 7,
      scope_type: 'COMPANY',
      company_code: 1,
      branch_code: null,
      valid_until: null,
    });
  });

  it('explica por que a atribuição não foi enviada quando falta o papel', async () => {
    await render();
    fixture.componentInstance.abrir('papel');
    fixture.detectChanges();

    fixture.componentInstance.confirmar();
    fixture.detectChanges();

    const service = TestBed.inject(UsuariosService);
    expect(service.atribuirPapel).not.toHaveBeenCalled();
    expect(fixture.nativeElement.textContent).toContain(
      'Selecione o papel que será atribuído.',
    );
  });

  it('exibe a falha ao carregar o catálogo em vez de encerrar silenciosamente', async () => {
    const papeisService = TestBed.inject(PapeisService);
    vi.mocked(papeisService.listar).mockReturnValue(
      throwError(() => new Error('catálogo indisponível')),
    );
    await render();

    fixture.componentInstance.abrir('papel');
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain(
      'Não foi possível carregar os papéis disponíveis.',
    );
  });
});
