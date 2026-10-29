import { Component, EventEmitter, Input, Output, computed, signal } from '@angular/core';
import { OClass } from '../core/api.service';

/** Arbre des classes (rdfs:subClassOf) avec le nombre d'instances. */
@Component({
  selector: 'app-class-tree',
  template: `
    <div class="scroll">
      @for (c of tree(); track c.name) {
        <a class="cls" [class.on]="c.name === selected" [style.padding-left.px]="8 + c.depth * 14" (click)="select.emit(c.name)">
          {{ c.name }} <small>{{ c.count }}</small>
        </a>
      }
    </div>`,
})
export class ClassTreeComponent {
  private all = signal<OClass[]>([]);
  @Input() set classes(v: OClass[]) { this.all.set(v); }
  @Input() selected = '';
  @Output() select = new EventEmitter<string>();
  tree = computed(() => {
    const byParent = new Map<string, OClass[]>();
    this.all().forEach(c => byParent.set(c.parent ?? '', [...(byParent.get(c.parent ?? '') ?? []), c]));
    const out: (OClass & { depth: number })[] = [];
    const walk = (p: string, d: number) => (byParent.get(p) ?? []).forEach(c => { out.push({ ...c, depth: d }); walk(c.name, d + 1); });
    walk('', 0);
    return out;
  });
}
