
import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../core/api.service';

interface NlpResponse {
  question: string;
  classe: string;
  intention: string;
  sparql: string;
  resultats: Record<string, string>[];
}

@Component({
  selector: 'app-assistant',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="assistant-page">
      <div class="heading">
        <div class="logo">✦</div>
        <div>
          <h1>Assistant IA sémantique</h1>
          <p>Personnes & Organismes · NLP + SPARQL</p>
        </div>
      </div>

      <div class="panel">
        <h2>Posez votre question en français</h2>
        <p class="help">
          Recherchez des informations dans l'ontologie
          Éducation & Formation.
        </p>

        <textarea
          [(ngModel)]="question"
          placeholder="Ex : Affiche tous les apprenants"
          rows="3">
        </textarea>

        <button
          class="send"
          (click)="rechercher()"
          [disabled]="chargement || !question.trim()">
          {{ chargement ? 'Analyse en cours...' : '✦ Analyser avec NLP' }}
        </button>

        <div class="examples">
          <span>Exemples de questions :</span>

          <button (click)="exemple('Affiche tous les apprenants')">
            Apprenants
          </button>

          <button (click)="exemple('Liste les enseignants')">
            Enseignants
          </button>

          <button (click)="exemple('Montre les entreprises')">
            Entreprises
          </button>

          <button (click)="exemple('Combien de personnes ?')">
            Nombre de personnes
          </button>

          <button (click)="exemple('Liste les universités')">
            Universités
          </button>
        </div>
      </div>

      <div *ngIf="erreur" class="error">
        {{ erreur }}
      </div>

      <div *ngIf="resultat" class="result-section">
        <div class="panel">
          <h2>Analyse NLP</h2>

          <div class="analysis">
            <div>
              <span>Classe détectée</span>
              <strong>{{ resultat.classe }}</strong>
            </div>

            <div>
              <span>Intention</span>
              <strong>{{ resultat.intention }}</strong>
            </div>
          </div>
        </div>

        <div class="panel">
          <div class="section-title">
            <h2>Requête SPARQL générée</h2>
            <button class="copy" (click)="copierSparql()">
              Copier
            </button>
          </div>

          <pre>{{ resultat.sparql }}</pre>
        </div>

        <div class="panel">
          <h2>Résultats de l'ontologie</h2>

          <p class="count">
            {{ resultat.resultats.length }} ligne(s) retournée(s)
          </p>

          <div *ngIf="resultat.resultats.length === 0" class="empty">
            Aucun résultat trouvé dans l'ontologie.
          </div>

          <div class="table-wrapper"
               *ngIf="resultat.resultats.length > 0">
            <table>
              <thead>
                <tr>
                  <th *ngFor="let col of colonnes">{{ col }}</th>
                </tr>
              </thead>
              <tbody>
                <tr *ngFor="let ligne of resultat.resultats">
                  <td *ngFor="let col of colonnes">
                    {{ ligne[col] }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .assistant-page {
      max-width: 1050px;
      margin: 0 auto;
      padding: 30px 18px;
      font-family: Arial, sans-serif;
    }

    .heading {
      display: flex;
      align-items: center;
      gap: 16px;
      margin-bottom: 28px;
    }

    .logo {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 58px;
      height: 58px;
      border-radius: 16px;
      background: #e9f1ff;
      color: #2563eb;
      font-size: 34px;
    }

    h1 {
      margin: 0;
      font-size: 26px;
      color: #172554;
    }

    h2 {
      margin: 0 0 14px;
      font-size: 19px;
      color: #1e3a8a;
    }

    .heading p, .help, .count {
      color: #64748b;
      font-size: 14px;
    }

    .panel {
      background: white;
      padding: 26px;
      margin-bottom: 22px;
      border: 1px solid #e2e8f0;
      border-radius: 15px;
      box-shadow: 0 4px 15px rgba(0,0,0,.04);
    }

    textarea {
      box-sizing: border-box;
      width: 100%;
      padding: 15px;
      border: 1px solid #cbd5e1;
      border-radius: 10px;
      font-size: 15px;
      margin-top: 12px;
      resize: vertical;
      background: #ffffff;
      color: #1e293b;
    }

    textarea:focus {
      outline: none;
      border-color: #2563eb;
    }

    button {
      cursor: pointer;
      border-radius: 8px;
      padding: 10px 15px;
      border: none;
      font-weight: 600;
    }

    .send {
      background: #2563eb;
      color: white;
      margin-top: 15px;
    }

    .send:disabled {
      background: #94a3b8;
      cursor: not-allowed;
    }

    .examples {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 9px;
      margin-top: 22px;
      font-size: 13px;
      color: #64748b;
    }

    .examples button {
      background: #eff6ff;
      color: #1d4ed8;
      font-size: 12px;
    }

    .analysis {
      display: flex;
      flex-wrap: wrap;
      gap: 15px;
    }

    .analysis div {
      background: #eff6ff;
      padding: 16px;
      border-radius: 10px;
      min-width: 160px;
    }

    .analysis span {
      display: block;
      color: #64748b;
      margin-bottom: 9px;
      font-size: 13px;
    }

    .analysis strong {
      color: #1d4ed8;
    }

    .section-title {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
    }

    .copy {
      background: #e2e8f0;
      color: #334155;
    }

    pre {
      background: #0f172a;
      color: #bfdbfe;
      padding: 20px;
      border-radius: 10px;
      overflow-x: auto;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      font-size: 13px;
    }

    .table-wrapper { overflow-x: auto; }

    table {
      border-collapse: collapse;
      width: 100%;
      margin-top: 15px;
    }

    th, td {
  padding: 13px;
  border-bottom: 1px solid #e2e8f0;
  text-align: left;
        }

        td {
        color: #1e293b;
        background: #ffffff;
        }

    tbody tr:hover td {
    background: #f1f5f9;
    }

    th {
      background: #eff6ff;
      color: #1e40af;
    }

    .error {
      background: #fee2e2;
      color: #b91c1c;
      padding: 15px;
      margin-bottom: 20px;
      border-radius: 10px;
    }

    .empty {
      color: #64748b;
      padding: 20px 0;
    }
  `]
})
export class AssistantComponent {
  private api = inject(ApiService);

  question = '';
  chargement = false;
  erreur = '';
  resultat: NlpResponse | null = null;
  colonnes: string[] = [];

  exemple(texte: string) {
    this.question = texte;
    this.rechercher();
  }

  rechercher() {
    const question = this.question.trim();
    if (!question || this.chargement) return;

    this.chargement = true;
    this.erreur = '';
    this.resultat = null;
    this.colonnes = [];

    this.api.nlp(question).subscribe({
      next: (data: NlpResponse) => {
        this.resultat = data;
        this.colonnes = data.resultats.length
          ? Object.keys(data.resultats[0])
          : [];
        this.chargement = false;
      },
      error: (err) => {
        this.erreur = err.error?.error ||
          'Impossible de contacter le serveur Flask.';
        this.chargement = false;
      }
    });
  }

  async copierSparql() {
    if (!this.resultat) return;

    try {
      await navigator.clipboard.writeText(this.resultat.sparql);
    } catch {
      this.erreur = 'Copie impossible depuis ce navigateur.';
    }
  }
}
