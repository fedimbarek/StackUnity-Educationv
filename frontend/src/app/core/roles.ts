// Rôles du front (miroir de backend/roles.py : le rôle vient de la classe de la Personne liée au compte).
// Un rôle « personnel » ne voit que SON dashboard + les modules listés ici. « admin » et « user » (anciens comptes) voient tout.
export const FULL_ACCESS = ['admin', 'user'];

export const ROLE_LABELS: Record<string, string> = {
  admin: 'Administrateur', user: 'Utilisateur', apprenant: 'Apprenant', enseignant: 'Enseignant', medical: 'Personnel médical',
  responsable_club: 'Responsable de club', tuteur: 'Tuteur', tuteur_entreprise: "Tuteur d'entreprise",
};

// Pages accessibles par rôle (ids des routes). Pas de 'personnes', 'inscriptions', 'bourses' ni 'sante' pour un apprenant :
// ces modules listent les données de tout le monde ; l'apprenant retrouve les siennes dans son dashboard.
// Pour ouvrir plus de pages à un rôle : ajouter l'id ici. Outils (sparql, ia, scenario, proprietes) : admin uniquement.
export const ACCESS: Record<string, string[]> = {
  apprenant: ['formations', 'matieres', 'clubs', 'organismes', 'espaces', 'vie'],
  enseignant: ['formations', 'matieres', 'clubs', 'organismes', 'espaces'],
  medical: ['sante', 'espaces'],
  responsable_club: ['clubs', 'espaces', 'organismes'],
  tuteur: ['formations', 'organismes'],
  tuteur_entreprise: ['organismes', 'formations'],
};

export const isFull = (role: string) => FULL_ACCESS.includes(role);
export const canAccess = (role: string, page: string) => isFull(role) || (ACCESS[role] ?? []).includes(page);
