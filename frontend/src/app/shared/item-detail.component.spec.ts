import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Detail } from '../core/api.service';
import { ItemDetailComponent } from './item-detail.component';

describe('ItemDetailComponent difficulty action', () => {
  const detail: Detail = {
    id: 'Math_01',
    label: 'Mathématiques',
    types: ['MatiereTechnique'],
    properties: [],
    incoming: [],
  };

  let fixture: ComponentFixture<ItemDetailComponent>;
  let component: ItemDetailComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ItemDetailComponent],
    }).compileComponents();
    fixture = TestBed.createComponent(ItemDetailComponent);
    component = fixture.componentInstance;
    component.detail = detail;
  });

  it('shows one estimate action for the selected subject and emits its RDF identifier', () => {
    component.showDifficultyPrediction = true;
    const estimate = jasmine.createSpy('estimate');
    component.estimateDifficulty.subscribe(estimate);
    fixture.detectChanges();

    const buttons = Array.from(fixture.nativeElement.querySelectorAll('button')) as HTMLButtonElement[];
    expect(buttons.filter(button => button.textContent?.trim() === 'Estimer').length).toBe(1);
    buttons.find(button => button.textContent?.trim() === 'Estimer')!.click();

    expect(estimate).toHaveBeenCalledOnceWith('Math_01');
  });

  it('does not show the estimate action for other entity details', () => {
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).not.toContain('Estimer');
  });
});
