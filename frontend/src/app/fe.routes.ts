import { Routes } from '@angular/router';

import { authGuard } from './core/auth/auth.guard';

export const FE_ROUTES: Routes = [
  {
    path: '',
    children: [
      { path: '', pathMatch: 'full', redirectTo: 'painel' },
      {
        path: 'login',
        loadComponent: () => import('./features/login/login').then((m) => m.LoginPage),
        title: 'Entrar | SGPD',
      },
      {
        path: '',
        canActivate: [authGuard],
        loadComponent: () =>
          import('./core/layout/authenticated-layout').then((m) => m.AuthenticatedLayout),
        children: [
          {
            path: 'painel',
            loadComponent: () => import('./features/painel/painel').then((m) => m.PainelPage),
            title: 'Painel | SGPD',
          },
          {
            path: 'senha',
            loadComponent: () => import('./features/senha/senha').then((m) => m.SenhaPage),
            title: 'Minha senha | SGPD',
          },
        ],
      },
      { path: '**', redirectTo: 'painel' },
    ],
  },
];
