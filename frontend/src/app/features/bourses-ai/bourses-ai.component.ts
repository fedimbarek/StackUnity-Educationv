import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';

// [à vérifier] adapter à la base d'URL utilisée par ton api.service / environment
const API = 'http://localhost:5000/api/bourses-ai';

@Component({
  selector: 'app-bourses-ai',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
  <div class="wrap">
    <h2>Assistant NLP — Bourses &amp; Inscriptions</h2>
    <p class="sub">Question en français → SPARQL (sans LLM) → résultats.</p>

    <div class="chips" *ngIf="examples.length">
      <button *ngFor="let e of examples" (click)="question = e; ask()">{{ e }}</button>
    </div>
    <p class="warn" *ngIf="examplesError">Exemples indisponibles : {{ examplesError }}</p>

    <div class="row">
      <input [(ngModel)]="question" (keyup.enter)="ask()" placeholder="Ex. Quels apprenants ont une bourse ?" />
      <button class="go" (click)="ask()" [disabled]="loading">{{ loading ? '...' : 'Demander' }}</button>
    </div>

    <p *ngIf="res && !res.ok" class="err">{{ res.error }}</p>

    <ng-container *ngIf="res">
      <div *ngIf="res.ok && res.type === 'ask'" class="ask">Réponse : <b>{{ res.answer ? 'OUI' : 'NON' }}</b></div>

      <div class="tw" *ngIf="res.ok && res.type === 'select'">
        <table>
          <tr><th *ngFor="let c of res.columns">{{ c }}</th></tr>
          <tr *ngFor="let r of res.rows"><td *ngFor="let v of r">{{ v }}</td></tr>
        </table>
      </div>
      <p *ngIf="res.ok && res.type === 'select' && !res.rows.length">Aucun résultat.</p>

      <details *ngIf="res.sparql" open><summary>Requête SPARQL générée</summary><pre>{{ res.sparql }}</pre></details>
      <details *ngIf="res.trace"><summary>Étapes du pipeline NLP</summary>
        <div *ngFor="let t of res.trace"><b>{{ t.etape }}</b> : {{ t.detail.join(' · ') }}</div>
      </details>
    </ng-container>
  </div>`,
  styles: [`
    .wrap{max-width:960px;margin:24px auto;padding:0 16px;color:inherit}
    .sub{opacity:.65}
    .row{display:flex;gap:8px;margin:12px 0}
    input{flex:1;padding:10px;border:1px solid #556;border-radius:8px;background:transparent;color:inherit}
    .go{padding:10px 18px;border:0;border-radius:8px;background:#3f51b5;color:#fff;cursor:pointer}
    .go:disabled{opacity:.6;cursor:wait}
    .chips button{margin:2px;padding:4px 10px;border:1px solid #556;border-radius:14px;background:transparent;color:inherit;cursor:pointer}
    .tw{overflow-x:auto}
    table{border-collapse:collapse;width:100%;margin:12px 0}
    th,td{border:1px solid #445;padding:6px 10px;text-align:left}
    th{background:rgba(127,127,160,.2)}
    pre{background:#1e1e1e;color:#d4d4d4;padding:12px;border-radius:8px;overflow:auto}
    details{margin:10px 0}
    .err{color:#ef5350}.warn{color:#ffb74d;font-size:.85rem}.ask{font-size:1.2rem;margin:12px 0}
  `],
})
export class BoursesAiComponent implements OnInit {
  private http = inject(HttpClient); // le JWT est ajouté par ton intercepteur existant
  question = '';
  examples: string[] = [];
  examplesError = '';
  res: any = null;
  loading = false;

  ngOnInit() {
    this.http.get<string[]>(`${API}/examples`).subscribe({
      next: e => (this.examples = e),
      error: e => (this.examplesError = this.describe(e)),
    });
  }

  ask() {
    if (!this.question.trim()) return;
    this.loading = true;
    this.res = null;
    this.http.post<any>(`${API}/ask`, { question: this.question }).subscribe({
      next: r => { this.res = r; this.loading = false; },
      error: e => { this.res = { ok: false, error: this.describe(e) }; this.loading = false; },
    });
  }

  private describe(e: any): string {
    if (e?.error?.error) return e.error.error;                       // message renvoyé par Flask
    if (e?.status === 0) return 'Serveur injoignable (backend arrêté, mauvaise URL ou CORS)';
    if (e?.status === 404) return 'HTTP 404 : blueprint non enregistré dans app.py (ou backend non redémarré)';
    if (e?.status === 401) return 'HTTP 401 : session expirée, reconnecte-toi';
    return `HTTP ${e?.status} ${e?.statusText || ''}`.trim();
  }
}