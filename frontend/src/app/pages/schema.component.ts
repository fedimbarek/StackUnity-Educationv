import { Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApiService, Prop } from '../core/api.service';
import { DATATYPES } from '../core/modules';

type PForm = { mode: 'create' | 'edit'; name: string; kind: 'object' | 'data'; domain: string; range: string; label: string };

/** Module « Propriétés » : CRUD des owl:ObjectProperty / owl:DatatypeProperty (/api/properties). */
@Component({
  selector: 'app-schema',
  imports: [FormsModule],
  template: `
    <h2>🔗 Propriétés <small class="muted">{{ props().length }}</small></h2>
    @if (form(); as f) {
      <div class="card form">
        <h4>{{ f.mode === 'create' ? 'Nouvelle propriété' : 'Modifier ' + f.name }}</h4>
        <input [(ngModel)]="f.name" [disabled]="f.mode === 'edit'" placeholder="Nom (ex: encadrePar)" />
        <select [(ngModel)]="f.kind" [disabled]="f.mode === 'edit'" (ngModelChange)="f.range = ''">
          <option value="object">ObjectProperty (relie 2 instances)</option>
          <option value="data">DatatypeProperty (valeur littérale)</option>
        </select>
        <input [(ngModel)]="f.domain" list="classes" placeholder="Domain : classe (optionnel)" />
        @if (f.kind === 'object') { <input [(ngModel)]="f.range" list="classes" placeholder="Range : classe (optionnel)" /> }
        @else { <select [(ngModel)]="f.range"><option value="">— type —</option>@for (t of types; track t) { <option>{{ t }}</option> }</select> }
        <input [(ngModel)]="f.label" placeholder="Label (fr)" />
        @if (err()) { <p class="err">{{ err() }}</p> }
        <button (click)="save()">Enregistrer</button> <button class="ghost" (click)="form.set(null)">Annuler</button>
      </div>
    }
    <datalist id="classes">@for (c of classes(); track c) { <option [value]="c"></option> }</datalist>
    <p><button (click)="start()">+ Nouvelle propriété</button>
       <input class="inline" placeholder="Filtrer…" [ngModel]="filter()" (ngModelChange)="filter.set($event)" /></p>
    <div class="card scroll">
      <table>
        <tr><th>Nom</th><th>Type</th><th>Domain</th><th>Range</th><th>Utilisée</th><th></th></tr>
        @for (p of shown(); track p.name) {
          <tr>
            <td>{{ p.name }}<br><small class="muted">{{ p.label }}</small></td><td>{{ p.kind }}</td>
            <td>{{ p.domain }}</td><td>{{ p.range }}</td><td>{{ p.usage }}×</td>
            <td><button class="small-btn" (click)="edit(p)">Modifier</button>
                <button class="small-btn danger" (click)="del(p)">Supprimer</button></td>
          </tr>
        }
      </table>
    </div>`,
})
export class SchemaComponent {
  private api = inject(ApiService);
  props = signal<Prop[]>([]); classes = signal<string[]>([]);
  form = signal<PForm | null>(null); err = signal(''); filter = signal('');
  types = DATATYPES;
  shown = computed(() => this.props().filter(p => p.name.toLowerCase().includes(this.filter().toLowerCase())));

  constructor() { this.load(); this.api.allClasses().subscribe(c => this.classes.set(c)); }
  load() { this.api.props().subscribe(p => this.props.set(p)); }
  start() { this.err.set(''); this.form.set({ mode: 'create', name: '', kind: 'object', domain: '', range: '', label: '' }); }
  edit(p: Prop) { this.err.set(''); this.form.set({ mode: 'edit', name: p.name, kind: p.kind, domain: p.domain ?? '', range: p.range ?? '', label: p.label }); }
  save() {
    const f = this.form(); if (!f) return;
    const call = f.mode === 'create' ? this.api.createProp(f) : this.api.updateProp(f.name, f);
    call.subscribe({ next: () => { this.form.set(null); this.load(); }, error: e => this.err.set(e.error?.error ?? 'Erreur') });
  }
  del(p: Prop) {
    if (!confirm(`Supprimer « ${p.name} » ? (${p.usage} triplet(s) qui l'utilisent seront supprimés)`)) return;
    this.api.deleteProp(p.name).subscribe(() => this.load());
  }
}
