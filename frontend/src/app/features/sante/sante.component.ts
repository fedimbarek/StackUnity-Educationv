import { Component } from '@angular/core';
import { ModulePageComponent } from '../../shared/module-page.component';
import { ModuleConfig, meta, tab } from '../../core/module.types';
import { NefziNlSearchComponent } from '../../shared/nefzi-nl-search.component';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
/** Module « Sante » : onglets = sous-entités de la classe racine ServiceMedical. */
export const SANTE: ModuleConfig = {
  ...meta('sante'),
  desc: 'Consultations, prévention, soutien psychologique, premiers secours, santé sportive et certificats médicaux.',
  root: 'ServiceMedical',
  tabs: [
    tab('Consultations', 'ConsultationMedicale', ['estGratuit', 'horairesOuverture'], ['nom', 'description', 'estGratuit', 'surRendezVous', 'horairesOuverture', 'telephoneService', 'assureParPersonnel', 'serviceLocaliseDans', 'serviceRattacheA', 'estOuvertA', 'dureeConsultationMinutes']),
    tab('Prévention', 'PreventionSante', ['estGratuit', 'horairesOuverture'], ['nom', 'description', 'estGratuit', 'surRendezVous', 'horairesOuverture', 'telephoneService', 'assureParPersonnel', 'serviceLocaliseDans', 'serviceRattacheA', 'estOuvertA']),
    tab('Soutien psychologique', 'SoutienPsychologique', ['estGratuit', 'horairesOuverture'], ['nom', 'description', 'estGratuit', 'surRendezVous', 'horairesOuverture', 'telephoneService', 'assureParPersonnel', 'serviceLocaliseDans', 'serviceRattacheA', 'estOuvertA', 'consultePar']),
    tab('Premiers secours', 'PremiersSecoursMedicaux', ['estGratuit', 'horairesOuverture'], ['nom', 'description', 'estGratuit', 'surRendezVous', 'horairesOuverture', 'telephoneService', 'assureParPersonnel', 'serviceLocaliseDans', 'serviceRattacheA', 'estOuvertA']),
    tab('Santé sportive', 'SanteSportive', ['estGratuit', 'horairesOuverture'], ['nom', 'description', 'estGratuit', 'surRendezVous', 'horairesOuverture', 'telephoneService', 'assureParPersonnel', 'serviceLocaliseDans', 'serviceRattacheA', 'estOuvertA']),
    tab('Certificats', 'CertificatMedical', ['dateCertificat', 'validiteMois'], ['nom', 'dateCertificat', 'validiteMois', 'certificatPour']),
  ],
};

@Component({
  selector: 'app-sante',
  imports: [CommonModule, FormsModule, ModulePageComponent, NefziNlSearchComponent],
  standalone: true,
  template: `
    <app-nefzi-nl-search
      context="sante"
      placeholder="Ex: Quels sont les services de santé gratuits ?">
    </app-nefzi-nl-search>
    <app-module-page [config]="config" />
  `,
})
export class SanteComponent { config = SANTE; }