import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApiService, QueryDef } from '../core/api.service';

@Component({
  selector: 'app-sparql',
  imports: [FormsModule],
  template: `
    <h2>Console SPARQL</h2>
    <p class="muted">Préfixes déjà déclarés : <code>: rdf: rdfs: owl: xsd:</code></p>
    <div class="toolbar">
      <button [class.ghost]="mode() !== 'read'" (click)="setMode('read')">Lecture (SELECT / ASK)</button>
      <button [class.ghost]="mode() !== 'write'" (click)="setMode('write')">Écriture CRUD (INSERT / DELETE) — admin</button>
    </div>
    @if (mode() === 'read') {
    <div class="toolbar">
      <select [ngModel]="selected" (ngModelChange)="pick($event)">
        <option value="">— Bibliothèque de {{ library().length }} requêtes —</option>
        @for (q of library(); track q.id) { <option [value]="q.id">{{ q.category }} · {{ q.title }}</option> }
      </select>
      @if (current()) { <small class="muted">{{ current()!.question }}</small> }
    </div>
    } @else {
      <div class="toolbar">
        @for (e of writeExamples; track e.label) { <button class="ghost small-btn" (click)="query = e.q">{{ e.label }}</button> }
      </div>
    }
    <textarea [(ngModel)]="query" rows="7"></textarea>
    <button (click)="run()">Exécuter</button>
    @if (error()) { <p class="err">{{ error() }}</p> }
    @if (message()) { <p class="ok">{{ message() }}</p> }
    @if (vars().length) {
      <div class="card scroll">
        <table>
          <tr>@for (v of vars(); track v) { <th>{{ v }}</th> }</tr>
          @for (r of rows(); track $index) { <tr>@for (v of vars(); track v) { <td>{{ r[v] }}</td> }</tr> }
        </table>
      </div>
      <p class="muted">{{ rows().length }} résultat(s)</p>
    }`,
})
export class SparqlComponent {
  private api = inject(ApiService);
  vars = signal<string[]>([]); rows = signal<any[]>([]); error = signal('');
  library = signal<QueryDef[]>([]); selected = ''; current = signal<QueryDef | null>(null);
  mode = signal<'read' | 'write'>('read'); message = signal('');
  query = 'SELECT ?classe WHERE { ?classe rdfs:subClassOf+ :Club }';
  writeExamples = [
    { label: 'CREATE (INSERT DATA)', q: 'INSERT DATA {\n  :ClubDemo a owl:NamedIndividual , :Club ;\n    rdfs:label "Club démo" ;\n    :capaciteMax 25 .\n}' },
    { label: 'UPDATE (DELETE/INSERT)', q: 'DELETE { :ClubDemo :capaciteMax ?old }\nINSERT { :ClubDemo :capaciteMax 40 }\nWHERE  { :ClubDemo :capaciteMax ?old }' },
    { label: 'DELETE', q: 'DELETE WHERE { :ClubDemo ?p ?o }' },
  ];
  setMode(m: 'read' | 'write') {
    this.mode.set(m); this.error.set(''); this.message.set(''); this.vars.set([]);
    this.query = m === 'read' ? 'SELECT ?classe WHERE { ?classe rdfs:subClassOf+ :Club }' : this.writeExamples[0].q;
  }

  constructor() { this.api.queries().subscribe(q => this.library.set(q)); }

  pick(id: string) {
    this.selected = id;
    const q = this.library().find(x => x.id === id) ?? null;
    this.current.set(q);
    if (q) { this.query = q.query; this.run(); }
  }

  run() {
    this.error.set(''); this.message.set('');
    if (this.mode() === 'write') {
      this.api.sparqlUpdate(this.query).subscribe({
        next: r => this.message.set(`Mise à jour appliquée : ${r.triples_before} → ${r.triples_after} triplets (${r.delta >= 0 ? '+' : ''}${r.delta}). formation_.ttl réécrit.`),
        error: e => this.error.set(e.error?.error ?? 'Erreur'),
      });
      return;
    }
    this.api.sparql(this.query).subscribe({
      next: r => { this.vars.set(r.vars); this.rows.set(r.rows); },
      error: e => { this.error.set(e.error?.error ?? 'Erreur'); this.vars.set([]); },
    });
  }
}
