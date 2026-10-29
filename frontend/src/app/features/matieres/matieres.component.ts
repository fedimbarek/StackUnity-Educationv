import { Component } from '@angular/core';
import { ModulePageComponent } from '../../shared/module-page.component';
import { ModuleConfig, meta, tab } from '../../core/module.types';

/** Module « Matieres » : onglets = sous-entités de la classe racine Matiere. */
export const MATIERES: ModuleConfig = {
  ...meta('matieres'),
  desc: 'Matières, séances, évaluations, ressources pédagogiques et outils numériques.',
  root: 'Matiere',
  tabs: [
    tab('Matières techniques', 'MatiereTechnique', ['codeMatiere', 'coefficient', 'nombreHeures'], ['nom', 'codeMatiere', 'coefficient', 'nombreHeures', 'matiereDeveloppe']),
    tab('Matières scientifiques', 'MatiereScientifique', ['codeMatiere', 'coefficient', 'nombreHeures'], ['nom', 'codeMatiere', 'coefficient', 'nombreHeures', 'matiereDeveloppe']),
    tab('Matières littéraires', 'MatiereLitteraire', ['codeMatiere', 'coefficient', 'nombreHeures'], ['nom', 'codeMatiere', 'coefficient', 'nombreHeures', 'matiereDeveloppe']),
    tab('Séances', 'Seance', ['dateSeance', 'heureDebut', 'lieuSeance'], ['nom', 'dateSeance', 'heureDebut', 'heureFin', 'animePar', 'lieuSeance', 'seanceDe']),
    tab('Évaluations', 'Evaluation', ['dateEvaluation', 'score'], ['nom', 'dateEvaluation', 'score', 'concerneFormation', 'attribueNiveau', 'evalue', 'associeRessource']),
    tab('Ressources', 'RessourcePedagogique', ['description'], ['nom', 'description']),
    tab('Outils numériques', 'OutilNumerique', ['versionOutil', 'urlOutil'], ['nom', 'versionOutil', 'urlOutil']),
  ],
};

@Component({
  selector: 'app-matieres',
  imports: [ModulePageComponent],
  template: `<app-module-page [config]="config" />`,
})
export class MatieresComponent { config = MATIERES; }
