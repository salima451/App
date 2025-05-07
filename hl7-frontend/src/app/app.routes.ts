import { Routes } from '@angular/router';
import { LayoutComponent } from './layout/layout.component';

export const routes: Routes = [
  {
    path: '',
    component: LayoutComponent,
    children: [
      { path: '', redirectTo: 'login', pathMatch: 'full' },
      { path: 'login', loadComponent: () => import('./login/login.component').then(m => m.LoginComponent) },
      { path: 'register', loadComponent: () => import('./register/register.component').then(m => m.RegisterComponent) },
      { path: 'messages', loadComponent: () => import('./messages/messages.component').then(m => m.MessagesComponent) },
      { path: 'stats', loadComponent: () => import('./stats/stats.component').then(m => m.StatsComponent) },
      { path: 'parcours-patient', loadComponent: () => import('./parcourspatient/parcourspatient.component').then(m => m.ParcoursComponent) },
      { path: 'tableaudebord', loadComponent: () => import('./tableaudebord/tableaudebord.component').then(m => m.TableaudebordComponent) },
    ]
  },
];
