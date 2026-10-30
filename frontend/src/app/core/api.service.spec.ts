import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { API } from './auth';
import { ApiService, DifficultyPredictionResponse } from './api.service';

describe('ApiService difficulty prediction', () => {
  let api: ApiService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [ApiService, provideHttpClient(), provideHttpClientTesting()],
    });
    api = TestBed.inject(ApiService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('posts the selected RDF identifier and returns the typed prediction', () => {
    const response: DifficultyPredictionResponse = {
      matiere: 'Mathématiques',
      difficulte: 'Difficile',
      methode: 'random_forest',
      confiance_pct: 85,
      confiance_avertissement: 'Score non calibré.',
      source_donnees: 'data.csv',
      indicateurs: {
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
      },
    };

    api.predictDifficulty('Math_01').subscribe(result => expect(result).toEqual(response));

    const request = httpMock.expectOne(`${API}/prediction/difficulte`);
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual({ id: 'Math_01' });
    request.flush(response);
  });
});
