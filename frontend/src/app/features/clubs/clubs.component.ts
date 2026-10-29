import { Component } from '@angular/core';
import { ModulePageComponent } from '../../shared/module-page.component';
import { ModuleConfig, meta, tab } from '../../core/module.types';

/** Module « Clubs » : onglets = sous-entités de la classe racine Club. */
export const CLUBS: ModuleConfig = {
  ...meta('clubs'),
  desc: 'Clubs étudiants (technologie, sport, musique, théâtre, humanitaire) et leurs événements.',
  root: 'Club',
  tabs: [
    tab('Technologie', 'ClubTechnologie', ['nombreMembres', 'jourSeance'], ['nom', 'description', 'anneeCreation', 'capaciteMax', 'nombreMembres', 'cotisation', 'jourSeance', 'dirigePar', 'encadrePar', 'clubDuDomaine']),
    tab('Sport', 'ClubSport', ['nombreMembres', 'jourSeance'], ['nom', 'description', 'anneeCreation', 'capaciteMax', 'nombreMembres', 'cotisation', 'jourSeance', 'dirigePar', 'encadrePar', 'clubDuDomaine']),
    tab('Musique', 'ClubMusique', ['nombreMembres', 'jourSeance'], ['nom', 'description', 'anneeCreation', 'capaciteMax', 'nombreMembres', 'cotisation', 'jourSeance', 'dirigePar', 'encadrePar', 'clubDuDomaine']),
    tab('Théâtre', 'ClubTheatre', ['nombreMembres', 'jourSeance'], ['nom', 'description', 'anneeCreation', 'capaciteMax', 'nombreMembres', 'cotisation', 'jourSeance', 'dirigePar', 'encadrePar', 'clubDuDomaine']),
    tab('Humanitaire', 'ClubHumanitaire', ['nombreMembres', 'jourSeance'], ['nom', 'description', 'anneeCreation', 'capaciteMax', 'nombreMembres', 'cotisation', 'jourSeance', 'dirigePar', 'encadrePar', 'clubDuDomaine']),
    tab('Événements', 'Evenement', ['dateEvenement', 'lieu'], ['nom', 'dateEvenement', 'lieu', 'description']),
  ],
};

@Component({
  selector: 'app-clubs',
  imports: [ModulePageComponent],
  template: `<app-module-page [config]="config" />`,
})
export class ClubsComponent { config = CLUBS; }
