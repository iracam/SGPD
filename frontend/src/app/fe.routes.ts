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
            path: 'processos',
            loadComponent: () =>
              import('./features/processos/processos').then((m) => m.ProcessosPage),
            title: 'Processos | SGPD',
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
            path: 'processos/:uuid/valores',
            loadComponent: () =>
              import('./features/processo-valores/processo-valores').then(
                (m) => m.ProcessoValoresPage,
              ),
            title: 'Valores do processo | SGPD',
          },
          {
            path: 'processos/:uuid/encerramento',
            loadComponent: () =>
              import('./features/processo-encerramento/processo-encerramento').then(
                (m) => m.ProcessoEncerramentoPage,
              ),
            title: 'Encerramento do processo | SGPD',
          },
          {
            path: 'relatorios',
            loadComponent: () =>
              import('./features/relatorios/relatorios').then((m) => m.RelatoriosPage),
            title: 'Relatórios | SGPD',
          },
          {
            path: 'notificacoes',
            loadComponent: () =>
              import('./features/notificacoes/notificacoes').then((m) => m.NotificacoesPage),
            title: 'Notificações | SGPD',
          },
          {
            path: 'tarefas',
            loadComponent: () =>
              import('./features/tarefas/tarefas').then((m) => m.TarefasPage),
            title: 'Minhas tarefas | SGPD',
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
            path: 'operacao',
            canActivate: [superadminGuard],
            loadComponent: () =>
              import('./features/operacao/operacao').then((m) => m.OperacaoPage),
            title: 'Operação | SGPD',
          },
          {
            path: 'configuracoes/email',
            canActivate: [superadminGuard],
            loadComponent: () =>
              import('./features/configuracoes/email-configuracao').then(
                (m) => m.EmailConfiguracaoPage,
              ),
            title: 'E-mail e notificações | SGPD',
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
