import { Component, EventEmitter, Input, OnInit, Output, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApiService, Detail, Individual, Prop } from '../core/api.service';
import { humanize } from '../core/module.types';

type Row = { property: string; value: string };

/** Formulaire typé : un champ par propriété de l'onglet (date, nombre, oui/non, liste d'instances…) + propriétés libres. */
@Component({
  selector: 'app-item-form',
  imports: [FormsModule],
  template: `
    <div class="card form">
      <h4>{{ initial ? 'Modifier ' + id : 'Nouveau : ' + type }}</h4>
      <div class="fgrid">
        <label class="fld"><span>Identifiant</span><input [(ngModel)]="id" [disabled]="!!initial" placeholder="ex: NouvelElement" /></label>
        <label class="fld"><span>Label affiché</span><input [(ngModel)]="label" /></label>
        @for (f of meta; track f.name) {
          <label class="fld"><span>{{ f.label || humanize(f.name) }}</span>
            @if (f.kind === 'object') {
              <select [(ngModel)]="vals[f.name]">
                <option value="">—</option>
                @for (o of opts(f); track o.id) { <option [value]="o.id">{{ o.label || o.id }}</option> }
              </select>
            } @else if (f.range === 'boolean') {
              <select [(ngModel)]="vals[f.name]"><option value="">—</option><option value="true">Oui</option><option value="false">Non</option></select>
            } @else { <input [type]="inputType(f)" step="any" [(ngModel)]="vals[f.name]" /> }
          </label>
        }
      </div>
      <h5>Autres propriétés</h5>
      @for (r of extra; track $index) {
        <div class="row">
          <select [(ngModel)]="r.property"><option value="">— propriété —</option>@for (p of extraOptions(); track p) { <option [value]="p">{{ p }}</option> }</select>
          <input [(ngModel)]="r.value" list="all-ids" placeholder="valeur ou identifiant d'instance" />
          <button class="ghost" (click)="extra.splice($index, 1)">✕</button>
        </div>
      }
      <button class="ghost" (click)="extra.push({ property: '', value: '' })">+ Propriété</button>
      <datalist id="all-ids">@for (i of ids; track i.id) { <option [value]="i.id"></option> }</datalist>
      @if (error) { <p class="err">{{ error }}</p> }
      <button (click)="submit()">Enregistrer</button> <button class="ghost" (click)="cancel.emit()">Annuler</button>
    </div>`,
})
export class ItemFormComponent implements OnInit {
  private api = inject(ApiService);
  humanize = humanize;
  @Input({ required: true }) module!: string;
  @Input({ required: true }) type!: string;
  @Input({ required: true }) fields!: string[];
  @Input({ required: true }) props!: Prop[];
  @Input() initial: Detail | null = null;
  @Input() error = '';
  @Output() save = new EventEmitter<any>();
  @Output() cancel = new EventEmitter<void>();

  id = ''; label = '';
  vals: Record<string, any> = {};
  extra: Row[] = [];
  meta: Prop[] = []; allowed: string[] = []; ids: Individual[] = [];
  private options: Record<string, Individual[]> = {};

  ngOnInit() {
    this.meta = this.fields.map(f => this.props.find(p => p.name === f)).filter((p): p is Prop => !!p);
    if (this.initial) {
      this.id = this.initial.id; this.label = this.initial.label;
      for (const r of this.initial.properties) {
        if (this.fields.includes(r.property) && !(r.property in this.vals)) this.vals[r.property] = r.value;
        else this.extra.push({ property: r.property, value: r.value });
      }
    }
    this.api.classProps(this.module, this.type).subscribe(p => (this.allowed = p));
    this.api.allIndividuals().subscribe(r => (this.ids = r));
    for (const f of this.meta) if (f.kind === 'object' && f.range)
      this.api.individualsOf(f.range).subscribe(r => (this.options[f.range!] = r));
  }

  opts(f: Prop): Individual[] {
    const list = this.options[f.range ?? ''] ?? [];
    const v = this.vals[f.name];
    return v && !list.some(o => o.id === v) ? [...list, { id: v }] : list;
  }
  inputType(f: Prop) {
    if (f.range === 'date') return 'date';
    if (f.range === 'time') return 'time';
    return ['integer', 'decimal', 'float', 'double', 'gYear'].includes(f.range ?? '') ? 'number' : 'text';
  }
  extraOptions() { return [...new Set([...this.allowed, ...this.extra.map(r => r.property).filter(Boolean)])].sort(); }

  submit() {
    const rows: Row[] = [
      ...this.meta.filter(m => this.vals[m.name] != null && String(this.vals[m.name]).trim() !== '')
                  .map(m => ({ property: m.name, value: String(this.vals[m.name]).trim() })),
      ...this.extra.filter(r => r.property && r.value),
    ];
    this.save.emit({ mode: this.initial ? 'edit' : 'create', id: this.id.trim(), type: this.type, label: this.label, properties: rows });
  }
}
