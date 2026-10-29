import { Component, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ApiService, MyDashboard } from '../core/api.service';
import { AuthService } from '../core/auth';
import { canAccess } from '../core/roles';

/** Tableau de bord PERSONNEL : affiché à la place du dashboard général pour les comptes liés à une Personne de l'ontologie.
 *  Tout vient de GET /api/me/dashboard (le contenu dépend du rôle ; le front ne fait que l'afficher). */
@Component({
  selector: 'app-my-dashboard',
  imports: [RouterLink],
  template: `
    @if (error()) { <p class="err">{{ error() }}</p> }
    @else if (!d()) { <p class="muted">Chargement de votre espace…</p> }
    @else {
      <section class="me-head">
        <div>
          <span class="pill role">{{ d()!.profile }}{{ d()!.type && d()!.type !== d()!.profile ? ' · ' + d()!.type : '' }}</span>
          <h1>Bonjour {{ d()!.person.name }}</h1>
          <p class="lead">{{ d()!.subtitle }}</p>
        </div>
        @if (d()!.person.fields.length) {
          <div class="card me-card">
            @for (f of d()!.person.fields; track f.label) {
              <div class="kv"><small class="muted">{{ f.label }}</small>
                <span>@for (v of f.values; track $index) { <span class="chip">{{ v.t }}</span> }</span></div>
            }
          </div>
        }
      </section>

      <div class="grid stats">
        @for (s of d()!.stats; track s.label) {
          <a class="card stat click" (click)="scrollTo(s.target)"><span>{{ s.value }}</span><small>{{ s.label }}</small></a>
        }
      </div>

      @if (!filled().length) {
        <div class="card" style="margin-top:24px">
          <h3>Votre espace est prêt</h3>
          <p class="muted">Aucune donnée n'est encore rattachée à votre profil dans l'ontologie. Elles apparaîtront ici dès qu'un administrateur les aura renseignées.</p>
        </div>
      }

      @for (sec of filled(); track sec.key) {
        <div class="card sec-card" [id]="'sec-' + sec.key">
          <h3>{{ sec.icon }} {{ sec.title }} <small class="muted">{{ sec.rows.length }}</small></h3>
          <div class="scroll">
            <table>
              <thead><tr>@for (c of sec.columns; track c) { <th>{{ c }}</th> }</tr></thead>
              <tbody>
                @for (r of sec.rows; track $index) {
                  <tr>@for (c of r; track $index) {
                    <td>@if (c.id && c.m && can(c.m)) { <a [routerLink]="'/' + c.m" [queryParams]="{ open: c.id }">{{ c.t }}</a> } @else { {{ c.t }} }</td>
                  }</tr>
                }
              </tbody>
            </table>
          </div>
        </div>
      }

      @if (filled().length && empty().length) {
        <p class="muted small" style="margin-top:20px">Sans données pour l'instant : {{ emptyTitles() }}.</p>
      }
    }`,
})
export class MyDashboardComponent {
  private api = inject(ApiService);
  private auth = inject(AuthService);
  d = signal<MyDashboard | null>(null); error = signal('');
  filled = computed(() => this.d()?.sections.filter(s => s.rows.length) ?? []);
  empty = computed(() => this.d()?.sections.filter(s => !s.rows.length) ?? []);
  emptyTitles = computed(() => this.empty().map(s => s.title.toLowerCase()).join(', '));

  constructor() {
    this.api.myDashboard().subscribe({ next: d => this.d.set(d), error: e => this.error.set(e.error?.error ?? 'Impossible de charger votre tableau de bord') });
  }
  can(page: string) { return canAccess(this.auth.role(), page); }
  scrollTo(key: string) { document.getElementById('sec-' + key)?.scrollIntoView({ behavior: 'smooth', block: 'start' }); }
}
