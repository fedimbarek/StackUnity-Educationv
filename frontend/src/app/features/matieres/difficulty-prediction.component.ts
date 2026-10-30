import { Component, Input, OnChanges, SimpleChanges, inject, signal } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import {
  ApiService,
  DifficultyIndicators,
  DifficultyPredictionResponse,
} from '../../core/api.service';

const INDICATOR_ROWS: { key: keyof DifficultyIndicators; label: string; suffix?: string }[] = [
  { key: 'moyenne', label: 'Moyenne' },
  { key: 'note_minimale', label: 'Note minimale' },
  { key: 'note_maximale', label: 'Note maximale' },
  { key: 'taux_reussite', label: 'Taux de réussite', suffix: '%' },
  { key: 'taux_echec', label: 'Taux d’échec', suffix: '%' },
  { key: 'ecart_type', label: 'Écart-type' },
  { key: 'nombre_evaluations', label: 'Nombre d’évaluations' },
  { key: 'nombre_resultats', label: 'Nombre de résultats' },
  { key: 'evaluations_ambigues', label: 'Évaluations ambiguës' },
  { key: 'seuil_reussite', label: 'Seuil de réussite' },
  { key: 'coefficient', label: 'Coefficient' },
  { key: 'nombre_heures', label: 'Heures de cours' },
  { key: 'nombre_competences', label: 'Compétences associées' },
  { key: 'taux_reussite_formation', label: 'Réussite des formations liées', suffix: '%' },
];

function isDifficultyIndicators(value: unknown): value is DifficultyIndicators {
  return typeof value === 'object' && value !== null
    && INDICATOR_ROWS.every(row => {
      const indicator = (value as Record<string, unknown>)[row.key];
      return typeof indicator === 'number' || indicator === null;
    });
}

@Component({
  selector: 'app-difficulty-prediction',
  template: `
    <section class="card difficulty-panel" aria-labelledby="difficulty-title">
      <h3 id="difficulty-title">Estimer la difficulté d’une matière</h3>
      <p class="muted small">Sélectionnez une matière dans la liste, puis utilisez le bouton « Estimer » de sa fiche.</p>

      @if (busy()) {
        <p class="muted" role="status" aria-live="polite">Calcul de la difficulté en cours…</p>
      }
      @if (error()) { <p class="err" role="alert">{{ error() }}</p> }

      @if (prediction(); as result) {
        <div class="difficulty-result" aria-live="polite">
          <h4>Résultat pour {{ result.matiere }}</h4>
          <p><strong>Difficulté : {{ result.difficulte }}</strong></p>
         
          @if (result.confiance_pct !== undefined) {
            <p><strong>Score indicatif du modèle : {{ result.confiance_pct }}%</strong></p>
            <p class="muted small">{{ result.confiance_avertissement }}</p>
          }
        </div>
      }
      @if (indicators(); as values) {
        <h4>Indicateurs</h4>
        <dl class="difficulty-indicators">
          @for (row of indicatorRows; track row.key) {
            <div><dt>{{ row.label }}</dt><dd>{{ values[row.key] ?? 'Non disponible' }}{{ values[row.key] === null ? '' : row.suffix ?? '' }}</dd></div>
          }
        </dl>
      }
    </section>`,
  styles: [`
    .difficulty-panel { margin-bottom: 18px; }
    .difficulty-indicators { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 10px; margin: 0; }
    .difficulty-indicators div { background: var(--bg2); border: 1px solid var(--line); border-radius: 3px; padding: 10px; }
    .difficulty-indicators dt { color: var(--muted); font-size: 12px; }
    .difficulty-indicators dd { margin: 2px 0 0; font-weight: 600; }
  `],
})
export class DifficultyPredictionComponent implements OnChanges {
  private api = inject(ApiService);

  @Input() request: { id: string; nonce: number } | null = null;
  busy = signal(false);
  error = signal('');
  prediction = signal<DifficultyPredictionResponse | null>(null);
  indicators = signal<DifficultyIndicators | null>(null);
  indicatorRows = INDICATOR_ROWS;

  ngOnChanges(changes: SimpleChanges) {
    const request = changes['request']?.currentValue as { id: string; nonce: number } | null;
    if (request) this.predict(request.id);
  }

  private predict(id: string) {
    if (!id || this.busy()) return;

    this.busy.set(true);
    this.error.set('');
    this.prediction.set(null);
    this.indicators.set(null);
    this.api.predictDifficulty(id).subscribe({
      next: result => {
        this.prediction.set(result);
        this.indicators.set(result.indicateurs);
        this.busy.set(false);
      },
      error: (failure: HttpErrorResponse) => {
        if (isDifficultyIndicators(failure.error?.indicateurs)) {
          this.indicators.set(failure.error.indicateurs);
        }
        this.error.set(this.errorMessage(failure.status));
        this.busy.set(false);
      },
    });
  }

  private errorMessage(status: number): string {
    switch (status) {
      case 400: return 'L’identifiant de la matière est invalide. Sélectionnez une matière de la liste puis réessayez.';
      case 404: return 'Cette matière est introuvable dans les données du serveur.';
      case 422: return 'Estimation indisponible : aucune donnée exploitable n’est associée à cette matière.';
      case 500: return 'Une erreur interne est survenue pendant la prédiction. Réessayez ultérieurement.';
      case 0: return 'Le serveur est inaccessible. Vérifiez votre connexion puis réessayez.';
      default: return 'La prédiction n’a pas pu être effectuée. Réessayez ultérieurement.';
    }
  }
}
