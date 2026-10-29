import { Injectable, inject, signal } from '@angular/core';
import { HttpClient, HttpInterceptorFn } from '@angular/common/http';
import { CanActivateFn, Router } from '@angular/router';
import { tap } from 'rxjs';
import { canAccess } from './roles';

export const API = 'http://localhost:5000/api';

export interface AuthResponse { token: string; username: string; role: string; person: string | null; name: string; profile: string; type: string; }
export interface ProfileOption {
  role: string; label: string;
  classes: { name: string; label: string }[];                  // types possibles pour une NOUVELLE personne
  persons: { id: string; label: string; type: string }[];      // personnes de l'ontologie encore libres
}
export interface RegisterPayload { username: string; password: string; role: string; person?: string; name?: string; type?: string; }

@Injectable({ providedIn: 'root' })
export class AuthService {
  private http = inject(HttpClient);
  private router = inject(Router);
  user = signal<string | null>(localStorage.getItem('username'));
  // anciens jetons (sans rôle mémorisé) => « user » : accès complet comme avant
  role = signal<string>(localStorage.getItem('role') ?? 'user');
  name = signal<string>(localStorage.getItem('name') ?? localStorage.getItem('username') ?? '');
  profile = signal<string>(localStorage.getItem('profile') ?? '');

  get token() { return localStorage.getItem('token'); }

  login(username: string, password: string) {
    return this.http.post<AuthResponse>(`${API}/auth/login`, { username, password }).pipe(tap(r => this.save(r)));
  }
  register(p: RegisterPayload) {
    return this.http.post<AuthResponse>(`${API}/auth/register`, p).pipe(tap(r => this.save(r)));
  }
  profiles = () => this.http.get<ProfileOption[]>(`${API}/auth/profiles`);

  private save(r: AuthResponse) {
    for (const [k, v] of Object.entries({ token: r.token, username: r.username, role: r.role, name: r.name, profile: r.profile }))
      localStorage.setItem(k, v ?? '');
    this.user.set(r.username); this.role.set(r.role); this.name.set(r.name); this.profile.set(r.profile);
  }
  logout() {
    localStorage.clear();
    this.user.set(null); this.role.set('user'); this.name.set(''); this.profile.set('');
    this.router.navigate(['/login']);
  }
}

// Ajoute le token à chaque requête ; déconnecte si le serveur répond 401
export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const auth = inject(AuthService);
  const t = auth.token;
  return next(t ? req.clone({ setHeaders: { Authorization: `Bearer ${t}` } }) : req).pipe(
    tap({ error: e => { if (e.status === 401 && !req.url.includes('/auth/')) auth.logout(); } })
  );
};

export const authGuard: CanActivateFn = () => {
  const ok = !!inject(AuthService).token;
  return ok || inject(Router).createUrlTree(['/login']);
};

// Page réservée selon le rôle (ex. un apprenant ne peut pas ouvrir /sparql ni /personnes) : retour au dashboard
export const accessGuard: CanActivateFn = route => {
  const page = route.routeConfig?.path ?? '';
  return canAccess(inject(AuthService).role(), page) || inject(Router).createUrlTree(['/']);
};
