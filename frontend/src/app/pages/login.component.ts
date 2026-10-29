import { Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService, ProfileOption } from '../core/auth';
import { HeroArtComponent } from '../shared/art.component';

@Component({
  selector: 'app-login',
  imports: [FormsModule, HeroArtComponent],
  template: `
    <div class="landing hero">
      <div class="landing-text">
        <svg viewBox="0 0 64 64" width="34" height="34" aria-hidden="true">
          <polygon points="32,6 56,19 32,32 8,19" fill="#5aa9ff"/><polygon points="8,19 32,32 32,58 8,45" fill="#1a73f0"/><polygon points="32,32 56,19 56,45 32,58" fill="#0b4aa8"/>
        </svg>
        <h1>{{ signup() ? 'Créer un compte' : 'Connexion à StackUnity' }}</h1>
        <p class="lead">
          {{ signup() ? 'Choisissez votre profil : votre tableau de bord sera adapté à votre rôle.'
                      : 'Chaque profil (apprenant, enseignant, médical…) retrouve son propre tableau de bord.' }}
        </p>
        <div class="login">
          <input [(ngModel)]="username" placeholder="Nom d'utilisateur" />
          <input [(ngModel)]="password" type="password" placeholder="Mot de passe" (keyup.enter)="submit()" />

          @if (signup()) {
            <label class="fld"><span>Je suis…</span>
              <select [ngModel]="role()" (ngModelChange)="pickRole($event)">
                <option value="">— Choisir mon profil —</option>
                @for (p of profiles(); track p.role) { <option [value]="p.role">{{ p.label }}</option> }
              </select>
            </label>

            @if (current(); as p) {
              <div class="seg">
                <a [class.on]="!create()" (click)="create.set(false)" [class.off]="!p.persons.length">Je suis déjà dans l'ontologie</a>
                <a [class.on]="create()" (click)="create.set(true)">Nouveau profil</a>
              </div>
              @if (!create()) {
                <label class="fld"><span>Mon identité</span>
                  <select [(ngModel)]="person">
                    <option value="">— Choisir —</option>
                    @for (x of p.persons; track x.id) { <option [value]="x.id">{{ x.label }} ({{ x.type }})</option> }
                  </select>
                </label>
                <p class="muted small">Vous retrouverez les données déjà enregistrées à votre nom.</p>
              } @else {
                <input [(ngModel)]="fullName" placeholder="Nom complet" />
                @if (p.classes.length > 1) {
                  <label class="fld"><span>Type</span>
                    <select [(ngModel)]="type">
                      @for (c of p.classes; track c.name) { <option [value]="c.name">{{ c.label }}</option> }
                    </select>
                  </label>
                }
              }
            }
          }

          @if (error()) { <p class="err">{{ error() }}</p> }
          <div class="cta">
            <button (click)="submit()">{{ signup() ? "S'inscrire" : 'Se connecter' }}</button>
            <button class="ghost" (click)="toggle()">{{ signup() ? 'J’ai déjà un compte' : 'Créer un compte' }}</button>
          </div>
          @if (!signup()) {
            <p class="muted small">Administrateur : <code>admin</code> / <code>admin123</code><br />
              Profils de démonstration (mot de passe <code>demo123</code>) :
              <code>amira</code> apprenant · <code>ahmed</code> enseignant · <code>drsonia</code> médecin · <code>rim</code> resp. de club ·
              <code>mehdi</code> tuteur d'entreprise · <code>sami</code> tuteur</p>
          }
        </div>
      </div>
      <app-hero-art />
    </div>`,
})
export class LoginComponent {
  private auth = inject(AuthService);
  private router = inject(Router);
  username = ''; password = ''; person = ''; fullName = ''; type = '';
  signup = signal(false); error = signal('');
  profiles = signal<ProfileOption[]>([]);
  role = signal(''); create = signal(false);
  current = computed(() => this.profiles().find(p => p.role === this.role()) ?? null);

  toggle() {
    this.signup.set(!this.signup()); this.error.set('');
    if (this.signup() && !this.profiles().length)
      this.auth.profiles().subscribe({ next: p => this.profiles.set(p), error: () => this.error.set('Serveur injoignable (Flask lancé ?)') });
  }
  pickRole(r: string) {
    this.role.set(r); this.person = ''; this.error.set('');
    const p = this.profiles().find(x => x.role === r);
    this.type = p?.classes[0]?.name ?? '';
    this.create.set(!!p && !p.persons.length);               // aucune personne libre : on crée un nouveau profil
  }

  submit() {
    this.error.set('');
    let call;
    if (!this.signup()) call = this.auth.login(this.username, this.password);
    else {
      if (!this.role()) return this.error.set('Choisissez votre profil.');
      if (!this.create() && !this.person) return this.error.set('Choisissez votre identité dans la liste (ou « Nouveau profil »).');
      call = this.auth.register({
        username: this.username, password: this.password, role: this.role(),
        ...(this.create() ? { name: this.fullName, type: this.type } : { person: this.person }),
      });
    }
    call.subscribe({
      next: () => this.router.navigate(['/']),
      error: e => this.error.set(e.error?.error ?? 'Serveur injoignable (Flask lancé ?)'),
    });
  }
}
