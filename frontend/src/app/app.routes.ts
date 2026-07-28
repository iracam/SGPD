import { Routes } from '@angular/router';

export const routes: Routes = [
  { path: '', pathMatch: 'full', redirectTo: 'fe/painel' },
  {
    path: 'fe',
    loadChildren: () => import('./fe.routes').then((module) => module.FE_ROUTES),
  },
  { path: '**', redirectTo: 'fe/painel' },
];
