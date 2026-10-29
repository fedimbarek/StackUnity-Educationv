import { Component } from '@angular/core';
import { ModulePageComponent } from '../../shared/module-page.component';
import { ModuleConfig, meta, tab } from '../../core/module.types';

/** Module « Personnes » : onglets = sous-entités de la classe racine Personne. */
export const PERSONNES: ModuleConfig = {
  ...meta('personnes'),
  desc: 'Enseignants, apprenants, tuteurs, personnel médical, responsables de club et administrateurs.',
  root: 'Personne',
  tabs: [
    tab('Enseignants', 'Enseignant', ['email', 'telephone'], ['nom', 'email', 'telephone', 'dateNaissance', 'appartientADepartement', 'enseigneMatiere']),
    tab('Apprenants', 'Apprenant', ['email', 'moyenneGenerale'], ['nom', 'email', 'telephone', 'dateNaissance', 'moyenneGenerale', 'inscritA', 'niveauDeLangue']),
    tab('Personnel médical', 'PersonnelMedical', ['specialiteMedicale', 'email'], ['nom', 'email', 'telephone', 'specialiteMedicale']),
    tab('Tuteurs', 'Tuteur', ['email', 'telephone'], ['nom', 'email', 'telephone', 'tutore']),
    tab('Tuteurs entreprise', 'TuteurEntreprise', ['email', 'telephone'], ['nom', 'email', 'telephone']),
    tab('Responsables de club', 'ResponsableClub', ['email', 'telephone'], ['nom', 'email', 'telephone']),
    tab('Administrateurs', 'Administrateur', ['email', 'telephone'], ['nom', 'email', 'telephone']),
  ],
};

@Component({
  selector: 'app-personnes',
  imports: [ModulePageComponent],
  template: `<app-module-page [config]="config" />`,
})
export class PersonnesComponent { config = PERSONNES; }
