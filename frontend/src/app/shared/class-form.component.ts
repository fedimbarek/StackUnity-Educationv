import { Component, EventEmitter, Input, OnInit, Output } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { OClass } from '../core/api.service';

/** Formulaire de création / modification d'une classe (nom, label, description, parent). */
@Component({
  selector: 'app-class-form',
  imports: [FormsModule],
  template: `
    <div class="card form">
      <h4>{{ mode === 'create' ? 'Nouvelle sous-classe de ' + m.parent : 'Modifier la classe ' + m.name }}</h4>
      <input [(ngModel)]="m.name" [disabled]="mode === 'edit'" placeholder="Nom (ex: Doctorant)" />
      <input [(ngModel)]="m.label" placeholder="Label (fr)" />
      <input [(ngModel)]="m.comment" placeholder="Description (rdfs:comment)" />
      @if (mode === 'edit' && m.parent) {
        <select [(ngModel)]="m.parent">@for (o of classes; track o.name) { @if (o.name !== m.name) { <option [value]="o.name">{{ o.name }}</option> } }</select>
      }
      @if (error) { <p class="err">{{ error }}</p> }
      <button (click)="save.emit(m)">Enregistrer</button> <button class="ghost" (click)="cancel.emit()">Annuler</button>
    </div>`,
})
export class ClassFormComponent implements OnInit {
  @Input() mode: 'create' | 'edit' = 'create';
  @Input() initial: { name: string; label: string; comment: string; parent: string } = { name: '', label: '', comment: '', parent: '' };
  @Input() classes: OClass[] = [];
  @Input() error = '';
  @Output() save = new EventEmitter<any>();
  @Output() cancel = new EventEmitter<void>();
  m = { name: '', label: '', comment: '', parent: '' };
  ngOnInit() { this.m = { ...this.initial }; }
}
