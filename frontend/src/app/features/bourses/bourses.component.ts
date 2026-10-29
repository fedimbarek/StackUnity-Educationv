import { Component } from '@angular/core';
import { ModulePageComponent } from '../../shared/module-page.component';
import { ModuleConfig, meta, tab } from '../../core/module.types';

/** Module « Bourses » : onglets = sous-entités de la classe racine Bourse. */
export const BOURSES: ModuleConfig = {
  ...meta('bourses'),
  desc: 'Bourses de mérite, sociales et de mobilité.',
  root: 'Bourse',
  tabs: [
    tab('Mérite', 'BourseMerite', ['montantBourse'], ['nom', 'description', 'montantBourse', 'financePar']),
    tab('Sociales', 'BourseSociale', ['montantBourse'], ['nom', 'description', 'montantBourse', 'financePar']),
    tab('Mobilité', 'BourseMobilite', ['montantBourse'], ['nom', 'description', 'montantBourse', 'financePar']),
  ],
};

@Component({
  selector: 'app-bourses',
  imports: [ModulePageComponent],
  template: `<app-module-page [config]="config" />`,
})
export class BoursesComponent { config = BOURSES; }
