import { Component, EventEmitter, Input, Output } from '@angular/core';
import { Individual } from '../core/api.service';

export interface Column { prop: string; label: string; }

/** Tableau d'instances : colonnes propres à chaque sous-entité. */
@Component({
  selector: 'app-item-table',
  template: `
    <div class="scroll">
      <table>
        <tr><th>Label</th>@for (c of columns; track c.prop) { <th>{{ c.label }}</th> }<th>Classe</th></tr>
        @for (r of rows; track r.id) {
          <tr class="click" [class.on]="r.id === selectedId" (click)="open.emit(r.id)">
            <td>{{ r.label || r.id }}<br><small class="muted">{{ r.id }}</small></td>
            @for (c of columns; track c.prop) { <td>{{ r.cols?.[c.prop] }}</td> }
            <td class="muted">{{ r.type }}</td>
          </tr>
        } @empty { <tr><td [attr.colspan]="columns.length + 2" class="muted">Aucune instance.</td></tr> }
      </table>
    </div>`,
})
export class ItemTableComponent {
  @Input() rows: Individual[] = [];
  @Input() columns: Column[] = [];
  @Input() selectedId: string | null = null;
  @Output() open = new EventEmitter<string>();
}
