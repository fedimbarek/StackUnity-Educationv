import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { AiAnswer, ApiService, Individual } from '../core/api.service';

/** Assistant IA : 3 usages de l'IA branchés sur l'ontologie (question→SPARQL, recommandation, explication). */
@Component({
  selector: 'app-ai',
  imports: [FormsModule],
  template: `
    <h2>Assistant NLP → SPARQL
      @if (status()) {
        <small class="pill">spaCy : {{ status()!.tools['spacy'] ? 'actif' : 'repli' }}</small>
        <small class="pill">NLTK : {{ status()!.tools['nltk'] ? 'actif' : 'repli' }}</small>
      }
    </h2>
    <p class="muted">Traducteur intelligent : la question en français est analysée (lemmatisation, racines, entités de l'ontologie, intention, contraintes)
      puis transformée en requête SPARQL exécutée par le serveur. Aucun LLM distant : uniquement des bibliothèques de NLP.</p>

    <div class="card">
      <h3>1. Poser une question en français</h3>
      <div class="examples">
        @for (e of examples; track e) { <button class="ghost small-btn" (click)="question = e; ask()">{{ e }}</button> }
      </div>
      <input [(ngModel)]="question" placeholder="Ex : Quels apprenants ont une bourse ?" (keyup.enter)="ask()" />
      <button (click)="ask()" [disabled]="busy()">{{ busy() ? 'Analyse…' : 'Demander' }}</button>
      @if (error()) { <p class="err">{{ error() }}</p> }
      @if (res(); as r) {
        <div class="bubble">{{ r.answer }}</div>
        @if (r.warning) { <p class="muted small">⚠ {{ r.warning }}</p> }
        @if (r.trace; as t) {
          <details open>
            <summary class="muted">Étapes du pipeline NLP</summary>
            <p class="small"><b>1. Analyse</b> (spaCy / NLTK) :
              @for (k of t.tokens; track $index) { <span class="chip" [title]="k.lemma + ' · ' + k.pos">{{ k.text }}<small> → {{ k.stem }}</small></span> }</p>
            <p class="small"><b>2. Entités de l'ontologie</b> :
              @for (e of t.entities; track $index) { <span class="chip ent">{{ e.text }} → {{ e.kind }}:{{ e.name }}{{ e.fuzzy ? ' (approx.)' : '' }}</span> }
              @if (!t.entities.length) { <em class="muted">aucune</em> }</p>
            <p class="small"><b>3. Intention</b> : {{ t.intent.join(', ') || 'liste (SELECT)' }}
              @if (t.constraints.length) { · <b>contraintes</b> : {{ t.constraints.join(', ') }} }</p>
            @for (n of t.notes; track n) { <p class="small muted">ℹ {{ n }}</p> }
          </details>
        }
        @if (r.sparql) {
          <details open><summary class="muted">4. Requête SPARQL générée</summary><pre>{{ r.sparql }}</pre></details>
        }
        @if (r.vars.length && r.vars[0] !== 'ASK') {
          <div class="scroll">
            <table>
              <tr>@for (v of r.vars; track v) { <th>{{ v }}</th> }</tr>
              @for (row of r.rows; track $index) { <tr>@for (v of r.vars; track v) { <td>{{ row[v] }}</td> }</tr> }
            </table>
          </div>
        }
      }
    </div>

    <div class="two">
      <div class="card">
        <h3>2. Recommandations pour un apprenant</h3>
        <p class="muted small">Pistes (clubs, stages, matières, ateliers) qui développent des compétences que l'apprenant n'a pas encore.</p>
        <select [(ngModel)]="learner"><option value="">— choisir un apprenant —</option>
          @for (l of learners(); track l.id) { <option [value]="l.id">{{ l.label || l.id }}</option> }
        </select>
        <button (click)="recommend()" [disabled]="!learner">Recommander</button>
        @if (reco(); as r) {
          <div class="bubble">{{ r.text }}</div>
          <table>
            <tr><th>Piste</th><th>Compétences nouvelles</th><th>Score</th></tr>
            @for (i of r.items; track i.id) { <tr><td>{{ i.label }}</td><td>{{ i.competences }}</td><td>{{ i.score }}</td></tr> }
          </table>
        }
      </div>

      <div class="card">
        <h3>3. Expliquer un individu</h3>
        <p class="muted small">Transforme les triplets d'une fiche en texte lisible.</p>
        <select [(ngModel)]="subject"><option value="">— choisir un individu —</option>
          @for (l of everyone(); track l.id) { <option [value]="l.id">{{ l.label || l.id }}</option> }
        </select>
        <button (click)="explain()" [disabled]="!subject">Expliquer</button>
        @if (fiche(); as f) { <div class="bubble">{{ f.text }}</div> }
      </div>
    </div>`,
})
export class AiComponent {
  private api = inject(ApiService);
  status = signal<{ engine: string; tools: Record<string, string | null>; llm: boolean } | null>(null);
  learners = signal<Individual[]>([]); everyone = signal<Individual[]>([]);
  res = signal<AiAnswer | null>(null); reco = signal<any>(null); fiche = signal<any>(null);
  busy = signal(false); error = signal('');
  question = ''; learner = ''; subject = '';
  examples = ['Quels apprenants ont une bourse ?', 'Combien de membres par club ?', 'Que sais-tu sur Amira ?',
              'Quels clubs ont plus de 20 membres ?', 'Quelles matières ont un coefficient entre 2 et 4 ?', 'Quel club a le plus de membres ?'];

  constructor() {
    this.api.aiStatus().subscribe(s => this.status.set(s));
    this.api.individualsOf('Apprenant').subscribe(l => this.learners.set(l));
    this.api.allIndividuals().subscribe(l => this.everyone.set(l));
  }
  ask() {
    if (this.question.trim().length < 3) return;
    this.busy.set(true); this.error.set('');
    this.api.aiAsk(this.question).subscribe({
      next: r => { this.res.set(r); this.busy.set(false); },
      error: e => { this.error.set(e.error?.error ?? 'Erreur serveur'); this.busy.set(false); },
    });
  }
  recommend() { this.api.aiRecommend(this.learner).subscribe({ next: r => this.reco.set(r), error: e => this.error.set(e.error?.error ?? 'Erreur') }); }
  explain() { this.api.aiExplain(this.subject).subscribe({ next: r => this.fiche.set(r), error: e => this.error.set(e.error?.error ?? 'Erreur') }); }
}
