import { Component, EventEmitter, Input, Output } from '@angular/core';
import { Detail } from '../core/api.service';

/** Fiche d'une instance : propriétés, liens vers d'autres instances, relations entrantes. */
@Component({
  selector: 'app-item-detail',
  template: `
    <h4>{{ detail.label }}
      <button class="small-btn" (click)="edit.emit()">Modifier</button>
      <button class="small-btn danger" (click)="remove.emit()">Supprimer</button></h4>
    <p>@for (t of detail.types; track t) { <span class="tag">{{ t }}</span> }</p>
    <table>
      @for (p of detail.properties; track $index) {
        <tr><td class="muted">{{ p.property }}</td>
            <td>{{ p.value }} @if (p.node) { <a (click)="navigate.emit(p.value)">→</a> }</td></tr>
      }
    </table>
    @if (detail.incoming.length) {
      <h5>Référencé par</h5>
      @for (r of detail.incoming; track $index) { <div><a (click)="navigate.emit(r.source)">{{ r.source }}</a> <small class="muted">({{ r.property }})</small></div> }
    }`,
})
export class ItemDetailComponent {
  @Input({ required: true }) detail!: Detail;
  @Output() edit = new EventEmitter<void>();
  @Output() remove = new EventEmitter<void>();
  @Output() navigate = new EventEmitter<string>();
}
