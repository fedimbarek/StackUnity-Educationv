import { Component, EventEmitter, Input, OnInit, Output, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { ApiService, Detail, Individual, Prop } from '../core/api.service';
import { EntityTab, humanize } from '../core/module.types';
import { ItemTableComponent } from './item-table.component';
import { ItemDetailComponent } from './item-detail.component';
import { ItemFormComponent } from './item-form.component';

/** CRUD complet d'UNE sous-entité (un onglet) : liste, filtre, fiche, création, modification, suppression. */
@Component({
  selector: 'app-entity-crud',
  imports: [FormsModule, ItemTableComponent, ItemDetailComponent, ItemFormComponent],
  template: `
    @if (form(); as f) {
      <app-item-form [module]="module" [type]="tab.cls" [fields]="tab.fields" [props]="props()" [initial]="f.initial" [error]="err()"
                     (save)="save($event)" (cancel)="form.set(null)" />
    }
    <p class="toolbar">
      <button (click)="create()">+ Nouveau</button>
      <input class="inline" placeholder="Filtrer…" [ngModel]="filter()" (ngModelChange)="filter.set($event)" />
      <span class="muted">{{ shown().length }} / {{ rows().length }} {{ tab.title.toLowerCase() }}</span>
    </p>
    <div class="two">
      <section class="card">
        <app-item-table [rows]="shown()" [columns]="columns()" [selectedId]="detail()?.id ?? null" (open)="open($event)" />
      </section>
      <section class="card">
        @if (detail(); as d) {
          <app-item-detail [detail]="d" (edit)="edit(d)" (remove)="remove(d)" (navigate)="go($event)" />
        } @else { <p class="muted">Sélectionne une ligne pour voir sa fiche.</p> }
      </section>
    </div>`,
})
export class EntityCrudComponent implements OnInit {
  private api = inject(ApiService);
  private router = inject(Router);
  @Input({ required: true }) module!: string;
  @Input({ required: true }) tab!: EntityTab;
  @Input() openId: string | null = null;
  @Output() changed = new EventEmitter<void>();

  rows = signal<Individual[]>([]); props = signal<Prop[]>([]); detail = signal<Detail | null>(null);
  filter = signal(''); err = signal('');
  form = signal<{ initial: Detail | null } | null>(null);

  columns = computed(() => this.tab.columns.map(c => ({ prop: c, label: this.props().find(p => p.name === c)?.label || humanize(c) })));
  shown = computed(() => {
    const f = this.filter().toLowerCase();
    return this.rows().filter(r => !f || (r.label ?? r.id).toLowerCase().includes(f) || r.id.toLowerCase().includes(f)
      || Object.values(r.cols ?? {}).some(v => v.toLowerCase().includes(f)));
  });

  ngOnInit() {
    this.api.props().subscribe(p => this.props.set(p));
    this.load();
    if (this.openId) this.open(this.openId);
  }
  load() { this.api.items(this.module, this.tab.cls, this.tab.columns).subscribe(r => this.rows.set(r)); }
  open(id: string) { this.api.item(this.module, id).subscribe({ next: d => this.detail.set(d), error: () => this.detail.set(null) }); }
  go(id: string) {                                    // lien vers une autre instance (même module ou autre module)
    this.api.individual(id).subscribe(d => {
      if (d.module === this.module) this.detail.set(d);
      else if (d.module) this.router.navigate(['/' + d.module], { queryParams: { open: id } });
    });
  }

  create() { this.err.set(''); this.form.set({ initial: null }); }
  edit(d: Detail) { this.err.set(''); this.form.set({ initial: d }); }
  save(p: any) {
    const call = p.mode === 'create' ? this.api.createItem(this.module, p) : this.api.updateItem(this.module, p.id, p);
    call.subscribe({
      next: () => { this.form.set(null); this.load(); this.open(p.id); this.changed.emit(); },
      error: e => this.err.set(e.error?.error ?? 'Erreur serveur'),
    });
  }
  remove(d: Detail) {
    if (!confirm(`Supprimer « ${d.id} » ? (${d.incoming.length} référence(s) entrante(s) seront aussi supprimées)`)) return;
    this.api.deleteItem(this.module, d.id).subscribe(() => { this.detail.set(null); this.load(); this.changed.emit(); });
  }
}
