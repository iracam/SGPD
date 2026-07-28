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
            path: 'usuarios',
            loadComponent: () => import('./features/usuarios/usuarios').then((m) => m.UsuariosPage),
            title: 'Usuários | SGPD',
          },
          {
            path: 'usuarios/:id',
            loadComponent: () =>
              import('./features/usuarios/usuario-detalhe').then((m) => m.UsuarioDetalhePage),
            title: 'Usuário | SGPD',
          },
          {
            path: 'papeis',
            loadComponent: () => import('./features/papeis/papeis').then((m) => m.PapeisPage),
            title: 'Papéis | SGPD',
          },
          {
            path: 'auditoria',
            loadComponent: () =>
              import('./features/auditoria/auditoria').then((m) => m.AuditoriaPage),
            title: 'Auditoria | SGPD',
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
