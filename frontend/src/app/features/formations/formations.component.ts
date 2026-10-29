import { Component } from '@angular/core';
import { ModulePageComponent } from '../../shared/module-page.component';
import { ModuleConfig, meta, tab } from '../../core/module.types';

/** Module « Formations » : onglets = sous-entités de la classe racine Domaine. */
export const FORMATIONS: ModuleConfig = {
  ...meta('formations'),
  desc: 'Formations, diplômes, compétences, certifications, parcours, niveaux, périodes académiques et domaines.',
  root: 'Domaine',
  tabs: [
    tab('Formations', 'Formation', ['duree', 'tauxReussite'], ['nom', 'description', 'duree', 'tauxReussite', 'appartientAuDomaine', 'estProposeePar', 'prepareDiplome', 'seDerouleEn', 'aPourMatiere']),
    tab('Licences', 'Licence', ['mention', 'delivrePar'], ['nom', 'mention', 'delivrePar', 'anneeObtention', 'creditsECTS']),
    tab('Masters', 'Master', ['mention', 'delivrePar'], ['nom', 'mention', 'delivrePar', 'anneeObtention', 'creditsECTS']),
    tab('Ingénieur', 'DiplomeIngenieur', ['mention', 'delivrePar'], ['nom', 'mention', 'delivrePar', 'anneeObtention', 'creditsECTS']),
    tab('Compétences', 'Competence', ['description'], ['nom', 'description', 'prerequisDe']),
    tab('Certifications', 'Certification', ['description'], ['nom', 'description', 'certifieCompetence']),
    tab('Parcours', 'ParcoursApprentissage', ['description'], ['nom', 'description', 'possedeEtape']),
    tab('Niveaux', 'Niveau', ['description'], ['nom', 'description']),
    tab('Périodes', 'PeriodeAcademique', ['dateDebut', 'dateFin'], ['nom', 'dateDebut', 'dateFin']),
    tab('Domaine Technologie', 'DomaineTechnologie', ['description'], ['nom', 'description']),
    tab('Domaine Sport', 'DomaineSport', ['description'], ['nom', 'description']),
    tab('Domaine Arts & Culture', 'DomaineArtsCulture', ['description'], ['nom', 'description']),
  ],
};

@Component({
  selector: 'app-formations',
  imports: [ModulePageComponent],
  template: `<app-module-page [config]="config" />`,
})
export class FormationsComponent { config = FORMATIONS; }
