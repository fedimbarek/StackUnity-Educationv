import { Component } from '@angular/core';
import { ModulePageComponent } from '../../shared/module-page.component';
import { ModuleConfig, meta, tab } from '../../core/module.types';

/** Module « Vie » : onglets = sous-entités de la classe racine ServiceVieEtudiante. */
export const VIE: ModuleConfig = {
  ...meta('vie'),
  desc: 'Hébergement, restauration, transport et orientation / emploi.',
  root: 'ServiceVieEtudiante',
  tabs: [
    tab('Hébergement', 'ServiceHebergement', ['lieu', 'estActif'], ['nom', 'description', 'lieu', 'estActif']),
    tab('Restauration', 'ServiceRestauration', ['lieu', 'estActif'], ['nom', 'description', 'lieu', 'estActif']),
    tab('Transport', 'ServiceTransport', ['lieu', 'estActif'], ['nom', 'description', 'lieu', 'estActif']),
    tab('Orientation & emploi', 'ServiceOrientationEmploi', ['lieu', 'estActif'], ['nom', 'description', 'lieu', 'estActif']),
  ],
};

@Component({
  selector: 'app-vie',
  imports: [ModulePageComponent],
  template: `<app-module-page [config]="config" />`,
})
export class VieComponent { config = VIE; }
