import { Routes } from '@angular/router';

import { authGuard } from './core/auth/auth.guard';
import { superadminGuard } from './core/auth/superadmin.guard';

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
            path: 'colaboradores',
            loadComponent: () =>
              import('./features/colaboradores/colaboradores').then(
                (m) => m.ColaboradoresPage,
              ),
            title: 'Abrir processo | SGPD',
          },
          {
            path: 'processos/:uuid/rascunho',
            loadComponent: () =>
              import('./features/processo-rascunho/processo-rascunho').then(
                (m) => m.ProcessoRascunhoPage,
              ),
            title: 'Rascunho do processo | SGPD',
          },
          {
            path: 'workflow-config',
            loadComponent: () =>
              import('./features/workflow-config/workflow-config').then(
                (m) => m.WorkflowConfigPage,
              ),
            title: 'Grupos e templates | SGPD',
          },
          {
            path: 'setores',
            loadComponent: () =>
              import('./features/setores/setores').then((m) => m.SetoresPage),
            title: 'Setores | SGPD',
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
            path: 'auditoria',
            loadComponent: () =>
              import('./features/auditoria/auditoria').then((m) => m.AuditoriaPage),
            title: 'Auditoria | SGPD',
          },
          {
            path: 'configuracoes',
            canActivate: [superadminGuard],
            loadComponent: () =>
              import('./features/configuracoes/configuracoes').then(
                (m) => m.ConfiguracoesPage,
              ),
            title: 'Configurações | SGPD',
          },
          {
            path: 'configuracoes/autenticacao',
            canActivate: [superadminGuard],
            loadComponent: () =>
              import('./features/configuracoes/ldap-configuracao').then(
                (m) => m.LdapConfiguracaoPage,
              ),
            title: 'LDAP e autenticação | SGPD',
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
