import { HttpErrorResponse } from '@angular/common/http';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Subject, of, throwError } from 'rxjs';
import {
  ApiService,
  DifficultyIndicators,
  DifficultyPredictionResponse,
  Individual,
} from '../../core/api.service';
import { DifficultyPredictionComponent } from './difficulty-prediction.component';

describe('DifficultyPredictionComponent', () => {
  const subject: Individual = { id: 'Math_01', label: 'Mathématiques', type: 'MatiereTechnique' };
  const indicators: DifficultyIndicators = {
    moyenne: 8.5,
    note_minimale: 4,
    note_maximale: 13,
    taux_reussite: 30,
    taux_echec: 70,
    ecart_type: 2.8,
    nombre_evaluations: 10,
    nombre_resultats: 10,
    evaluations_ambigues: 0,
    seuil_reussite: 10,
    coefficient: 3,
    nombre_heures: 60,
    nombre_competences: 2,
    taux_reussite_formation: null,
  };
  const response: DifficultyPredictionResponse = {
    matiere: 'Mathématiques',
    difficulte: 'Difficile',
    methode: 'regles_charge_pedagogique',
    indicateurs: indicators,
  };

  let api: jasmine.SpyObj<ApiService>;
  let fixture: ComponentFixture<DifficultyPredictionComponent>;
  let component: DifficultyPredictionComponent;

  beforeEach(async () => {
    api = jasmine.createSpyObj<ApiService>('ApiService', ['predictDifficulty']);
    api.predictDifficulty.and.returnValue(of(response));
    await TestBed.configureTestingModule({
      imports: [DifficultyPredictionComponent],
      providers: [{ provide: ApiService, useValue: api }],
    }).compileComponents();
    fixture = TestBed.createComponent(DifficultyPredictionComponent);
    component = fixture.componentInstance;
  });

  function requestPrediction() {
    fixture.componentRef.setInput('request', { id: subject.id, nonce: 1 });
    fixture.detectChanges();
  }

  it('shows instructions without a second selector or estimate button', () => {
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('select')).toBeNull();
    expect(fixture.nativeElement.querySelector('button')).toBeNull();
    expect(fixture.nativeElement.textContent).toContain('bouton « Estimer » de sa fiche');
  });

  it('shows a loading state and then the successful difficulty and indicators', () => {
    const pending = new Subject<DifficultyPredictionResponse>();
    api.predictDifficulty.and.returnValue(pending);
    requestPrediction();

    expect(component.busy()).toBeTrue();
    expect(fixture.nativeElement.textContent).toContain('Calcul de la difficulté en cours');
    expect(api.predictDifficulty).toHaveBeenCalledOnceWith(subject.id);

    pending.next(response);
    pending.complete();
    fixture.detectChanges();

    expect(component.busy()).toBeFalse();
    expect(fixture.nativeElement.querySelector('.difficulty-result').textContent).toContain('Difficile');
    expect(fixture.nativeElement.textContent).toContain('Taux de réussite');
    expect(fixture.nativeElement.textContent).toContain('30%');
    expect(fixture.nativeElement.textContent).toContain('pas un modèle ML entraîné');
  });

  it('explains a temporary 422 and does not invent a difficulty while showing available indicators', () => {
    const failure = new HttpErrorResponse({
      status: 422,
      error: { error: 'Résultats insuffisants.', indicateurs: { ...indicators } },
    });
    api.predictDifficulty.and.returnValue(throwError(() => failure));
    requestPrediction();

    expect(component.error()).toContain('aucune donnée exploitable');
    expect(fixture.nativeElement.querySelector('.difficulty-result')).toBeNull();
    expect(fixture.nativeElement.textContent).toContain('Nombre de résultats');
  });

  it('shows a specific message when the subject is not found', () => {
    api.predictDifficulty.and.returnValue(
      throwError(() => new HttpErrorResponse({ status: 404 })),
    );
    requestPrediction();

    expect(component.error()).toContain('introuvable');
    expect(fixture.nativeElement.querySelector('.difficulty-result')).toBeNull();
  });

  it('shows a clear message for other server errors', () => {
    api.predictDifficulty.and.returnValue(
      throwError(() => new HttpErrorResponse({ status: 500 })),
    );
    requestPrediction();

    expect(component.error()).toContain('erreur interne');
    expect(fixture.nativeElement.querySelector('.difficulty-result')).toBeNull();
  });

  it('renders unavailable note indicators without inventing values', () => {
    api.predictDifficulty.and.returnValue(of({
      ...response,
      indicateurs: {
        ...indicators,
        moyenne: null,
        taux_reussite: null,
        taux_echec: null,
        ecart_type: null,
        taux_reussite_formation: null,
        nombre_resultats: 0,
      },
    }));
    requestPrediction();

    expect(fixture.nativeElement.textContent).toContain('Non disponible');
    expect(fixture.nativeElement.textContent).toContain('Coefficient');
  });

  it('displays the Random Forest percentage as an indicative model score', () => {
    api.predictDifficulty.and.returnValue(of({
      ...response,
      methode: 'random_forest',
      confiance_pct: 85,
      confiance_avertissement: 'Score non calibré.',
      source_donnees: 'data.csv',
    }));
    requestPrediction();

    expect(fixture.nativeElement.textContent).toContain('Score indicatif du modèle : 85%');
    expect(fixture.nativeElement.textContent).toContain('Score non calibré.');
    expect(fixture.nativeElement.textContent).toContain('data.csv');
  });
});
