import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { ApiService } from '../core/api.service';
import { CubeComponent, HeroArtComponent } from '../shared/art.component';

@Component({
  selector: 'app-dashboard',
  imports: [RouterLink, FormsModule, CubeComponent, HeroArtComponent],
  template: `
    <section class="hero">
      <div class="hero-text">
        <h1>Gérez votre ontologie de formation</h1>
        <p class="lead">Dix modules, un seul graphe : parcourez les instances, modifiez les classes et interrogez les données en SPARQL.</p>
        <input class="search" placeholder="Rechercher dans toute l'ontologie (ex : python)…" [ngModel]="q()" (ngModelChange)="onSearch($event)" />
        @if (hits().length) {
          <div class="card hits">
            @for (h of hits(); track $index) {
              <a (click)="go(h)">{{ h.label }} <small class="muted">· {{ h.type }} · {{ h.module }}</small></a>
            }
          </div>
        }
        <div class="cta">
          <a class="btn" routerLink="/formations">Voir les formations</a>
          <a class="btn ghost" routerLink="/sparql">Console SPARQL</a>
          <a class="btn ghost" routerLink="/ia">Assistant IA</a>
        </div>
      </div>
      <app-hero-art />
    </section>

    <div class="grid stats">
      @for (s of statList(); track s[0]) { <div class="card stat"><span>{{ s[1] }}</span><small>{{ s[0] }}</small></div> }
    </div>

    <h2 class="center">Modules</h2>
    <div class="grid mods">
      @for (m of mods(); track m.id; let i = $index) {
        <a class="card mod" [routerLink]="'/' + m.id">
          <app-cube [i]="i" />
          <b>{{ m.title }}</b>
          <span class="muted">{{ m.desc }}</span>
          <small class="muted">{{ m.classes }} classes · {{ m.instances }} instances</small>
        </a>
      }
    </div>`,
})
export class DashboardComponent {
  private api = inject(ApiService);
  private router = inject(Router);
  statList = signal<[string, number][]>([]); mods = signal<any[]>([]);
  q = signal(''); hits = signal<any[]>([]);
  constructor() {
    this.api.stats().subscribe(s => this.statList.set(Object.entries(s)));
    this.api.modules().subscribe(m => this.mods.set(m));
  }
  onSearch(v: string) { this.q.set(v); v.length < 2 ? this.hits.set([]) : this.api.search(v).subscribe(r => this.hits.set(r)); }
  go(h: any) { this.router.navigate(['/' + h.module], { queryParams: { open: h.id } }); }
}
