import { Component } from '@angular/core';
import { ModulePageComponent } from '../../shared/module-page.component';
import { ModuleConfig, meta, tab } from '../../core/module.types';

/** Module « Espaces » : onglets = sous-entités de la classe racine Espace. */
export const ESPACES: ModuleConfig = {
  ...meta('espaces'),
  desc: 'Salles de cours, salles informatiques, amphithéâtres, départements et infirmerie.',
  root: 'Espace',
  tabs: [
    tab('Salles de cours', 'SalleDeCours', ['capaciteEspace'], ['nom', 'capaciteEspace', 'estSitueDans']),
    tab('Salles informatiques', 'SalleInformatique', ['capaciteEspace'], ['nom', 'capaciteEspace', 'estSitueDans']),
    tab('Amphithéâtres', 'Amphitheatre', ['capaciteEspace'], ['nom', 'capaciteEspace', 'estSitueDans']),
    tab('Départements', 'Departement', ['partieDe'], ['nom', 'description', 'partieDe', 'proposeFormation']),
    tab('Infirmeries', 'Infirmerie', ['capaciteEspace'], ['nom', 'capaciteEspace', 'estSitueDans']),
  ],
};

@Component({
  selector: 'app-espaces',
  imports: [ModulePageComponent],
  template: `<app-module-page [config]="config" />`,
})
export class EspacesComponent { config = ESPACES; }
