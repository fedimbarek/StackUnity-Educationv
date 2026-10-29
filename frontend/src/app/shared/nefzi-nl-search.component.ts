import { Component, Input, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../core/api.service';

@Component({
  selector: 'app-nefzi-nl-search',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="card" style="margin:16px 0">
      <h3>🧠 Recherche intelligente (NLP/TALN)</h3>
      <p class="muted small">
        Posez une question en français — <b>spaCy</b> + <b>NLTK</b> + <b>difflib</b> la traduisent en SPARQL.
      </p>

      <div class="toolbar">
        <input [(ngModel)]="question" [placeholder]="placeholder"
               (keyup.enter)="ask()" style="flex:1">
        <button (click)="ask()" [disabled]="loading()">
          {{ loading() ? '⏳ Analyse…' : '🔍 Rechercher' }}
        </button>
      </div>

      <div class="small muted" style="margin-top:8px">
        <b>Exemples :</b>
        @for (ex of examples(); track ex) {
          <span class="tag" style="cursor:pointer" (click)="setQ(ex)">{{ ex }}</span>
        }
      </div>

      @if (error()) { <p class="err" style="margin-top:12px">{{ error() }}</p> }

      @if (meta()) {
        <div style="margin-top:12px; font-size:12px">
          <b>Type :</b> <code>{{ meta().kind }}</code>
          · <b>Intentions :</b> <code>{{ meta().intent || '—' }}</code>
          · <b>spaCy :</b> {{ meta().spacy_used ? '✅' : '⚠️' }}
          · <b>NLTK :</b> {{ meta().nltk_used ? '✅' : '⚠️' }}

          @if (meta().constraints?.length) {
            · <b>Contraintes :</b>
            @for (c of meta().constraints; track c) { <span class="tag">{{ c }}</span> }
          }

          @if (meta().entities?.length) {
            · <b>Entités :</b>
            @for (e of meta().entities; track e.text) {
              <span class="tag">
                {{ e.text }} → {{ e.name }} ({{ e.kind }})
                @if (e.fuzzy) { <b>≈</b> }
              </span>
            }
          }

          @if (meta().notes?.length) {
            <div style="margin-top:6px; font-style:italic">
              @for (n of meta().notes; track n) {
                <p class="muted small">ℹ️ {{ n }}</p>
              }
            </div>
          }
        </div>
      }

      @if (sparqlText()) {
        <details style="margin-top:12px">
          <summary style="cursor:pointer; font-size:12px">
            <b>Requête SPARQL générée</b>
          </summary>
          <pre style="overflow:auto; font-size:11px; padding:8px; background:var(--bg2); border-radius:3px"><code>{{ sparqlText() }}</code></pre>
        </details>
      }

      @if (rows().length) {
        <p class="muted small" style="margin-top:12px">{{ rows().length }} résultat(s)</p>
        <table>
          <thead>
            <tr>@for (k of keys(); track k) { <th>{{ k }}</th> }</tr>
          </thead>
          <tbody>
            @for (r of rows(); track $index) {
              <tr>@for (k of keys(); track k) { <td>{{ r[k] ?? '—' }}</td> }</tr>
            }
          </tbody>
        </table>
      } @else if (!loading() && !error() && sparqlText()) {
        <p class="muted small">Aucun résultat.</p>
      }
    </div>
  `,
})
export class NefziNlSearchComponent implements OnInit {
  @Input() context: 'sante' | 'vie' | 'all' = 'all';
  @Input() placeholder = 'Ex: Quels sont les services de santé gratuits ?';

  private api = inject(ApiService);
  question = '';
  loading = signal(false);
  error = signal<string | null>(null);
  sparqlText = signal<string | null>(null);
  rows = signal<any[]>([]);
  meta = signal<any | null>(null);
  keys = signal<string[]>([]);
  examples = signal<string[]>([]);

  ngOnInit() {
    this.api.nlExamples().subscribe({
      next: r => {
        const ctx = this.context;
        const filtered =
          ctx === 'sante'
            ? r.examples.filter(e => /sant|psycho|gratuit|médec|medec|dentaire|stress|sans rendez/i.test(e))
            : ctx === 'vie'
            ? r.examples.filter(e => /vie|logement|transport|manger|héberg|navette|campus/i.test(e))
            : r.examples;
        this.examples.set(filtered.length ? filtered : r.examples);
      },
      error: () => this.examples.set([]),
    });
  }

  setQ(q: string) { this.question = q; this.ask(); }

  ask() {
    if (!this.question.trim()) return;
    this.loading.set(true); this.error.set(null);
    this.sparqlText.set(null); this.rows.set([]); this.meta.set(null);

    this.api.nlQuery(this.question).subscribe({
      next: r => {
        this.rows.set(r.rows); this.sparqlText.set(r.sparql); this.meta.set(r.meta);
        this.keys.set(r.rows.length ? Object.keys(r.rows[0]) : []);
        this.loading.set(false);
      },
      error: e => {
        this.error.set(e.error?.error || 'Erreur serveur');
        if (e.error?.sparql) this.sparqlText.set(e.error.sparql);
        if (e.error?.trace)  this.meta.set({ kind: 'error', trace: e.error.trace });
        this.loading.set(false);
      },
    });
  }
}