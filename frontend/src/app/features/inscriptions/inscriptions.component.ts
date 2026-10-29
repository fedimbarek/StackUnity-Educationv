import { Component } from '@angular/core';
import { ModulePageComponent } from '../../shared/module-page.component';
import { ModuleConfig, meta, tab } from '../../core/module.types';

/** Module « Inscriptions » : onglets = sous-entités de la classe racine Inscription. */
export const INSCRIPTIONS: ModuleConfig = {
  ...meta('inscriptions'),
  desc: 'Inscriptions administratives, pédagogiques et aux clubs.',
  root: 'Inscription',
  tabs: [
    tab('Administratives', 'InscriptionAdministrative', ['dateInscription', 'statutInscription'], ['nom', 'dateInscription', 'statutInscription', 'inscriptionDe', 'inscriptionPourPeriode']),
    tab('Pédagogiques', 'InscriptionPedagogique', ['dateInscription', 'statutInscription'], ['nom', 'dateInscription', 'statutInscription', 'inscriptionDe', 'inscriptionPourPeriode', 'inscriptionPourFormation']),
    tab('Clubs', 'InscriptionClub', ['dateInscription', 'statutInscription'], ['nom', 'dateInscription', 'statutInscription', 'inscriptionDe', 'inscriptionPourPeriode', 'inscriptionAuClub']),
  ],
};

@Component({
  selector: 'app-inscriptions',
  imports: [ModulePageComponent],
  template: `<app-module-page [config]="config" />`,
})
export class InscriptionsComponent { config = INSCRIPTIONS; }
