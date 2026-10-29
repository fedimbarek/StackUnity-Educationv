import { Component, Input, OnInit, computed, inject, signal } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { ApiService, OClass } from '../core/api.service';
import { ModuleConfig } from '../core/module.types';
import { EntityCrudComponent } from './entity-crud.component';
import { ClassManagerComponent } from './class-manager.component';

const CLASSES = '__classes';

/** Page d'un module : en-tête, onglets (un par sous-entité) + onglet « Classes » (schéma du module). */
@Component({
  selector: 'app-module-page',
  imports: [EntityCrudComponent, ClassManagerComponent],
  template: `
    <h2>{{ config.icon }} {{ config.title }} <small class="muted">{{ classes().length }} classes</small></h2>
    <p class="muted">{{ config.desc }}</p>
    <div class="tabs">
      @for (t of config.tabs; track t.cls) {
        <a class="tab" [class.on]="active() === t.cls" (click)="select(t.cls)">{{ t.title }} <span class="badge">{{ count(t.cls) }}</span></a>
      }
      <a class="tab" [class.on]="active() === CLASSES" (click)="select(CLASSES)">⚙ Classes</a>
    </div>
    @if (!ready()) { <p class="muted">Chargement…</p> }
    @else if (active() === CLASSES) {
      <app-class-manager [module]="config.id" [classes]="classes()" (changed)="loadClasses()" />
    } @else {
      @for (t of [currentTab()]; track t.cls) {
        <app-entity-crud [module]="config.id" [tab]="t" [openId]="openId()" (changed)="loadClasses()" />
      }
    }`,
})
export class ModulePageComponent implements OnInit {
  private api = inject(ApiService);
  private route = inject(ActivatedRoute);
  CLASSES = CLASSES;
  @Input({ required: true }) config!: ModuleConfig;
  classes = signal<OClass[]>([]); active = signal(''); ready = signal(false); openId = signal<string | null>(null);
  currentTab = computed(() => this.config.tabs.find(t => t.cls === this.active()) ?? this.config.tabs[0]);

  ngOnInit() {
    this.active.set(this.config.tabs[0].cls);
    this.api.classes(this.config.id).subscribe(cs => {
      this.classes.set(cs);
      const open = this.route.snapshot.queryParamMap.get('open');       // ?open=<id> : arrivée depuis la recherche / un lien
      if (open) this.api.individual(open).subscribe(d => {
        const parent = new Map(cs.map(c => [c.name, c.parent]));
        for (let c: string | null | undefined = d.types[0]; c; c = parent.get(c)) {
          const t = this.config.tabs.find(x => x.cls === c);
          if (t) { this.active.set(t.cls); break; }
        }
        this.openId.set(open); this.ready.set(true);
      });
      else this.ready.set(true);
    });
  }
  loadClasses() { this.api.classes(this.config.id).subscribe(cs => this.classes.set(cs)); }
  count(cls: string) { return this.classes().find(c => c.name === cls)?.count ?? 0; }
  select(c: string) { this.openId.set(null); this.active.set(c); }
}
