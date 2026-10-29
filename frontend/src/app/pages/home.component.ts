import { Component, computed, inject } from '@angular/core';
import { AuthService } from '../core/auth';
import { isFull } from '../core/roles';
import { DashboardComponent } from './dashboard.component';
import { MyDashboardComponent } from './my-dashboard.component';

/** Page d'accueil « / » : dashboard général pour admin (et anciens comptes), dashboard personnel pour les autres rôles. */
@Component({
  selector: 'app-home',
  imports: [DashboardComponent, MyDashboardComponent],
  template: `@if (personal()) { <app-my-dashboard /> } @else { <app-dashboard /> }`,
})
export class HomeComponent {
  private auth = inject(AuthService);
  personal = computed(() => !isFull(this.auth.role()));
}
