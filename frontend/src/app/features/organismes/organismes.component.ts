import { Component } from '@angular/core';
import { ModulePageComponent } from '../../shared/module-page.component';
import { ModuleConfig, meta, tab } from '../../core/module.types';

/** Module « Organismes » : onglets = sous-entités de la classe racine Organisme. */
export const ORGANISMES: ModuleConfig = {
  ...meta('organismes'),
  desc: 'Universités, entreprises, laboratoires et stages (PFE, initiation, recherche…).',
  root: 'Organisme',
  tabs: [
    tab('Universités', 'Universite', ['ville', 'secteurActivite'], ['nom', 'ville', 'secteurActivite', 'description']),
    tab('Entreprises', 'Entreprise', ['ville', 'secteurActivite'], ['nom', 'ville', 'secteurActivite', 'description']),
    tab('Laboratoires', 'Laboratoire', ['ville', 'secteurActivite'], ['nom', 'ville', 'secteurActivite', 'description']),
    tab('Stages', 'Stage', ['sujet', 'dureeSemaines', 'estRemunere'], ['nom', 'sujet', 'dureeSemaines', 'estRemunere', 'gratification', 'numeroConvention', 'dateDebut', 'dateFin', 'accueilliPar', 'estEffectuePar', 'encadreAcademique', 'superviseParTuteur', 'valideFormation']),
  ],
};

@Component({
  selector: 'app-organismes',
  imports: [ModulePageComponent],
  template: `<app-module-page [config]="config" />`,
})
export class OrganismesComponent { config = ORGANISMES; }
