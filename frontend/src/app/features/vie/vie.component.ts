import { Component } from '@angular/core';
import { ModulePageComponent } from '../../shared/module-page.component';
import { ModuleConfig, meta, tab } from '../../core/module.types';
<<<<<<< HEAD
import { NefziNlSearchComponent } from '../../shared/nefzi-nl-search.component';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { SANTE } from '../sante/sante.component';
=======
>>>>>>> 3d5aa3acacaab95058bb469d316a5a2236e830ce

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
<<<<<<< HEAD
  standalone: true,
  imports: [CommonModule, ModulePageComponent, NefziNlSearchComponent],
  template: `
    <app-nefzi-nl-search
      context="vie"
      placeholder="Ex: Quels sont les services d'hébergement ?">
    </app-nefzi-nl-search>
    <app-module-page [config]="config" />
  `,
})
export class VieComponent { config = VIE; }
=======
  imports: [ModulePageComponent],
  template: `<app-module-page [config]="config" />`,
})
export class VieComponent { config = VIE; }
>>>>>>> 3d5aa3acacaab95058bb469d316a5a2236e830ce
