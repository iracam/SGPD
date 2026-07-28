import { TestBed } from '@angular/core/testing';
import { Router, UrlTree, provideRouter } from '@angular/router';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { AuthService } from './auth.service';
import { superadminGuard } from './superadmin.guard';

describe('superadminGuard', () => {
  const ensureAuthenticated = vi.fn();
  const currentUser = vi.fn();

  beforeEach(() => {
    ensureAuthenticated.mockReset();
    currentUser.mockReset();
    TestBed.configureTestingModule({
      providers: [
        provideRouter([]),
        {
          provide: AuthService,
          useValue: { ensureAuthenticated, currentUser },
        },
      ],
    });
  });

  it('permite somente a sessão marcada como SuperAdmin pelo servidor', async () => {
    const { of, firstValueFrom } = await import('rxjs');
    ensureAuthenticated.mockReturnValue(of(true));
    currentUser.mockReturnValue({ is_superuser: true });

    const result = await TestBed.runInInjectionContext(() =>
      firstValueFrom(superadminGuard({} as never, {} as never) as never),
    );

    expect(result).toBe(true);
  });

  it('redireciona usuário comum para o painel', async () => {
    const { of, firstValueFrom } = await import('rxjs');
    ensureAuthenticated.mockReturnValue(of(true));
    currentUser.mockReturnValue({ is_superuser: false });

    const result = await TestBed.runInInjectionContext(() =>
      firstValueFrom(superadminGuard({} as never, {} as never) as never),
    );

    expect(result).toBeInstanceOf(UrlTree);
    expect(TestBed.inject(Router).serializeUrl(result as UrlTree)).toBe('/fe/painel');
  });
});
