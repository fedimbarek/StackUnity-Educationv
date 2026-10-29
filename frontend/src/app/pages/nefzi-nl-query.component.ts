import { Component } from '@angular/core';
import { NefziNlSearchComponent } from '../shared/nefzi-nl-search.component';

@Component({
  selector: 'app-nefzi-nl-query',
  standalone: true,
  imports: [NefziNlSearchComponent],
  template: `
    <h1>🧠 Assistant IA — Recherche libre</h1>
    <p class="lead">
      Posez n'importe quelle question sur l'ontologie. Le serveur détecte l'intention
      (spaCy + NLTK), résout les entités (difflib), génère et exécute la requête SPARQL.
    </p>
    <app-nefzi-nl-search
      context="all"
      placeholder="Ex: Quels services consulte Karim ?">
    </app-nefzi-nl-search>
  `,
})
export class NefziNlQueryComponent {}