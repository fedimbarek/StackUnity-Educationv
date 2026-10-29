import { Component, EventEmitter, Input, Output, computed, inject, signal } from '@angular/core';
import { ApiService, OClass } from '../core/api.service';
import { ClassTreeComponent } from './class-tree.component';
import { ClassFormComponent } from './class-form.component';

/** Onglet « Classes » d'un module : CRUD des classes (schéma) du module. */
@Component({
  selector: 'app-class-manager',
  imports: [ClassTreeComponent, ClassFormComponent],
  template: `
    @if (form(); as f) {
      <app-class-form [mode]="f.mode" [initial]="f.initial" [classes]="classes" [error]="err()" (save)="save($event)" (cancel)="form.set(null)" />
    }
    <div class="two">
      <section class="card"><h4>Hiérarchie</h4><app-class-tree [classes]="classes" [selected]="selected()" (select)="selected.set($event)" /></section>
      <section class="card">
        @if (current(); as c) {
          <h4>{{ c.name }}
            <button class="small-btn" (click)="create()">+ Sous-classe</button>
            <button class="small-btn" (click)="edit()">Modifier</button>
            <button class="small-btn danger" (click)="remove()">Supprimer</button></h4>
          <p><b>{{ c.label || '—' }}</b></p><p class="muted">{{ c.comment || 'Pas de description.' }}</p>
          <p>Parent : {{ c.parent || '(racine du module)' }} · {{ c.count }} instance(s)</p>
        } @else { <p class="muted">Sélectionne une classe.</p> }
      </section>
    </div>`,
})
export class ClassManagerComponent {
  private api = inject(ApiService);
  @Input({ required: true }) module!: string;
  private all = signal<OClass[]>([]);
  @Input() set classes(v: OClass[]) { this.all.set(v); }
  get classes() { return this.all(); }
  @Output() changed = new EventEmitter<void>();
  selected = signal(''); err = signal('');
  form = signal<{ mode: 'create' | 'edit'; initial: any } | null>(null);
  current = computed(() => this.all().find(c => c.name === this.selected()));

  create() { this.err.set(''); this.form.set({ mode: 'create', initial: { name: '', label: '', comment: '', parent: this.selected() } }); }
  edit() {
    const c = this.current(); if (!c) return;
    this.err.set(''); this.form.set({ mode: 'edit', initial: { name: c.name, label: c.label, comment: c.comment, parent: c.parent ?? '' } });
  }
  save(v: any) {
    const f = this.form(); if (!f) return;
    const call = f.mode === 'create' ? this.api.createClass(this.module, v) : this.api.updateClass(this.module, v.name, v);
    call.subscribe({ next: () => { this.form.set(null); this.selected.set(v.name); this.changed.emit(); }, error: e => this.err.set(e.error?.error ?? 'Erreur') });
  }
  remove() {
    const c = this.current(); if (!c || !confirm(`Supprimer la classe « ${c.name} » ?`)) return;
    this.api.deleteClass(this.module, c.name).subscribe({
      next: () => { this.selected.set(c.parent ?? ''); this.changed.emit(); },
      error: e => alert(e.error?.error ?? 'Erreur'),
    });
  }
}
