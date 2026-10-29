import { Component, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { Observable, map, switchMap } from 'rxjs';
import { ApiService } from '../core/api.service';
import { AuthService } from '../core/auth';

interface Result { text?: string; vars?: string[]; rows?: any[]; }
interface Step { title: string; desc: string; run: () => Observable<Result>; }

/** Scénario de démonstration : « Dossier 360° d'Amira » — chaque étape appelle réellement le backend. */
@Component({
  selector: 'app-scenario',
  imports: [RouterLink],
  template: `
    <h2>Scénario : le dossier 360° d'Amira</h2>
    <p class="muted">
      Amira Ben Salah, apprenante, veut faire le point sur son parcours : bourse, stage PFE, club, services de santé,
      compétences… puis savoir quoi développer ensuite. Le scénario traverse toute l'application :
      authentification → recherche → fiche → SPARQL → IA → recommandation.
      <a routerLink="/personnes">Ouvrir le module Personnes</a>
    </p>
    <div class="cta"><button (click)="runAll()" [disabled]="busy() !== null">▶ Tout exécuter</button></div>
    @for (s of steps; track s.title; let i = $index) {
      <div class="card step">
        <h3><span class="num">{{ i + 1 }}</span> {{ s.title }}</h3>
        <p class="muted">{{ s.desc }}</p>
        <button class="ghost" (click)="run(i)" [disabled]="busy() !== null">{{ results()[i] ? 'Relancer' : 'Exécuter' }}</button>
        @if (busy() === i) { <span class="muted"> …</span> }
        @if (results()[i]; as r) {
          @if (r.text) { <div class="bubble">{{ r.text }}</div> }
          @if (r.vars?.length) {
            <div class="scroll">
              <table>
                <tr>@for (v of r.vars ?? []; track v) { <th>{{ v }}</th> }</tr>
                @for (row of r.rows; track $index) { <tr>@for (v of r.vars ?? []; track v) { <td>{{ row[v] }}</td> }</tr> }
              </table>
            </div>
          }
        }
      </div>
    }`,
})
export class ScenarioComponent {
  private api = inject(ApiService);
  private auth = inject(AuthService);
  results = signal<Record<number, Result>>({});
  busy = signal<number | null>(null);

  steps: Step[] = [
    { title: 'Connexion et état de l\'ontologie',
      desc: 'Le front envoie le JWT à chaque requête ; le backend répond avec les statistiques du graphe (requêtes SPARQL d\'agrégat).',
      run: () => this.api.stats().pipe(map(s => ({
        text: `Connecté en tant que « ${this.auth.user()} » (jeton JWT valide).`,
        vars: ['indicateur', 'valeur'], rows: Object.entries(s).map(([indicateur, valeur]) => ({ indicateur, valeur })) }))) },
    { title: 'Recherche globale « amira »',
      desc: 'Recherche plein texte sur les labels de tous les modules (SPARQL CONTAINS).',
      run: () => this.api.search('amira').pipe(map(r => ({ vars: ['id', 'label', 'type', 'module'], rows: r }))) },
    { title: 'Fiche de l\'individu Amira',
      desc: 'Types, propriétés et relations de l\'individu — fiche globale commune à tous les modules.',
      run: () => this.api.individual('Amira').pipe(map(d => ({
        text: `${d.label} — types : ${d.types.join(', ')} — module : ${d.module}`,
        vars: ['property', 'value'], rows: d.properties }))) },
    { title: 'Requête SPARQL « dossier 360° »',
      desc: 'Requête UNION + BIND de la bibliothèque : bourse, stage, club, services, compétences et certifications en un seul tableau.',
      run: () => this.api.queries().pipe(
        map(q => q.find(x => x.id === 'dossier_amira')!),
        switchMap(q => this.api.sparql(q.query).pipe(map(r => ({ text: q.title, vars: r.vars, rows: r.rows }))))) },
    { title: 'Question en langage naturel (NLP → SPARQL)',
      desc: '« Quels étudiants ont une bourse ? » : le module NLP (spaCy + NLTK) analyse la phrase, génère le SPARQL et l\'exécute.',
      run: () => this.api.aiAsk('Quels étudiants ont une bourse ?').pipe(map(r => ({
        text: r.answer + (r.sparql ? '\n\nSPARQL : ' + r.sparql.replace(/\s+/g, ' ') : ''), vars: r.vars, rows: r.rows }))) },
    { title: 'Recommandation personnalisée',
      desc: 'Raisonnement sur le graphe : pistes qui développent des compétences qu\'Amira n\'a pas encore.',
      run: () => this.api.aiRecommend('Amira').pipe(map(r => ({
        text: r.text, vars: ['label', 'competences', 'score'], rows: r.items }))) },
  ];

  run(i: number) {
    this.busy.set(i);
    this.steps[i].run().subscribe({
      next: r => { this.results.update(m => ({ ...m, [i]: r })); this.busy.set(null); },
      error: e => { this.results.update(m => ({ ...m, [i]: { text: '⚠ ' + (e.error?.error ?? 'Erreur') } })); this.busy.set(null); },
    });
  }
  async runAll() {
    for (let i = 0; i < this.steps.length; i++) {
      await new Promise<void>(res => {
        this.busy.set(i);
        this.steps[i].run().subscribe({
          next: r => { this.results.update(m => ({ ...m, [i]: r })); this.busy.set(null); res(); },
          error: e => { this.results.update(m => ({ ...m, [i]: { text: '⚠ ' + (e.error?.error ?? 'Erreur') } })); this.busy.set(null); res(); },
        });
      });
    }
  }
}
