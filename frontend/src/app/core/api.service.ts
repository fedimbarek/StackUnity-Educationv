
import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { API } from './auth';

export interface OClass {
  name: string;
  parent: string | null;
  count: number;
  label: string;
  comment: string;
}

export interface Individual {
  id: string;
  label?: string;
  type?: string;
  cols?: Record<string, string>;
}

export interface Prop {
  name: string;
  kind: 'object' | 'data';
  domain: string | null;
  range: string | null;
  label: string;
  usage?: number;
}

export interface Detail {
  id: string;
  label: string;
  types: string[];
  module?: string | null;
  properties: {
    property: string;
    value: string;
    node?: boolean;
  }[];
  incoming: {
    source: string;
    property: string;
  }[];
}

// Dashboard personnalisé
export interface DashCell {
  t: string;
  id?: string;
  m?: string | null;
}

export interface DashSection {
  key: string;
  title: string;
  icon: string;
  empty: string;
  columns: string[];
  rows: DashCell[][];
}

export interface MyDashboard {
  role: string;
  profile: string;
  type: string;
  title: string;
  subtitle: string;

  person: {
    id: string;
    name: string;
    fields: {
      label: string;
      values: DashCell[];
    }[];
  };

  stats: {
    label: string;
    value: number;
    target: string;
  }[];

  sections: DashSection[];
}

// Bibliothèque de requêtes SPARQL
export interface QueryDef {
  id: string;
  category: string;
  title: string;
  question: string;
  query: string;
}

// NLP avancé des collègues
export interface NlpTrace {
  tools: Record<string, string | null>;
  tokens: {
    text: string;
    lemma: string;
    pos: string;
    stem: string;
  }[];
  entities: {
    text: string;
    kind: string;
    name: string;
    fuzzy: boolean;
  }[];
  intent: string[];
  constraints: string[];
  notes: string[];
}

export interface AiAnswer {
  question: string;
  engine: 'nlp';
  sparql: string | null;
  vars: string[];
  rows: any[];
  answer: string;
  warning?: string | null;
  trace: NlpTrace | null;
}

// NOUVEAU : Assistant NLP Personnes et Organismes
export interface NlpResponse {
  question: string;
  classe: string;
  intention: string;
  sparql: string;
  resultats: Record<string, string>[];
}

export interface DifficultyPredictionRequest {
  id: string;
}

export interface DifficultyIndicators {
  moyenne: number | null;
  note_minimale: number | null;
  note_maximale: number | null;
  taux_reussite: number | null;
  taux_echec: number | null;
  ecart_type: number | null;
  nombre_evaluations: number;
  nombre_resultats: number;
  evaluations_ambigues: number;
  seuil_reussite: number;
  coefficient: number | null;
  nombre_heures: number | null;
  nombre_competences: number;
  taux_reussite_formation: number | null;
}

export interface DifficultyPredictionResponse {
  matiere: string;
  difficulte: string;
  methode: 'random_forest' | 'regles_resultats' | 'regles_reussite_formation' | 'regles_charge_pedagogique';
  confiance_pct?: number;
  confiance_avertissement?: string;
  source_donnees?: string;
  avertissement?: string;
  indicateurs: DifficultyIndicators;
}

@Injectable({ providedIn: 'root' })
export class ApiService {

  private http = inject(HttpClient);

  // --- Dashboard personnalisé selon le rôle ---
  myDashboard = () =>
    this.http.get<MyDashboard>(`${API}/me/dashboard`);

  // --- Transversal ---
  modules = () =>
    this.http.get<any[]>(`${API}/modules`);

  stats = () =>
    this.http.get<Record<string, number>>(`${API}/stats`);

  search = (q: string) =>
    this.http.get<any[]>(`${API}/search`, { params: { q } });

  allIndividuals = () =>
    this.http.get<Individual[]>(`${API}/individuals`);

  individual = (id: string) =>
    this.http.get<Detail>(`${API}/individuals/${id}`);

  individualsOf = (cls: string) =>
    this.http.get<Individual[]>(
      `${API}/classes/${cls}/individuals`
    );

  allClasses = () =>
    this.http.get<string[]>(`${API}/classes`);

  // --- SPARQL ---
  sparqlUpdate = (update: string) =>
    this.http.post<{
      ok: boolean;
      triples_before: number;
      triples_after: number;
      delta: number;
    }>(`${API}/sparql/update`, { update });

  sparql = (query: string) =>
    this.http.post<{ vars: string[]; rows: any[] }>(
      `${API}/sparql`, { query }
    );

  queries = () =>
    this.http.get<QueryDef[]>(`${API}/queries`);

  // --- IA avancée des collègues ---
  aiStatus = () =>
    this.http.get<{
      engine: string;
      tools: Record<string, string | null>;
      llm: boolean;
    }>(`${API}/ai/status`);

  aiAsk = (question: string) =>
    this.http.post<AiAnswer>(
      `${API}/ai/ask`, { question }
    );

  aiExplain = (id: string) =>
    this.http.post<any>(
      `${API}/ai/explain`, { id }
    );

  aiRecommend = (id: string) =>
    this.http.get<any>(
      `${API}/ai/recommend/${id}`
    );

  // --- NOUVEAU : Assistant IA Dhia NLP + SPARQL ---
  nlp = (question: string) =>
    this.http.post<NlpResponse>(
      `${API}/nlp`,
      { question }
    );

  // --- Prédiction de difficulté d'une matière ---
  predictDifficulty = (id: string) =>
    this.http.post<DifficultyPredictionResponse>(
      `${API}/prediction/difficulte`,
      { id } satisfies DifficultyPredictionRequest
    );

  // --- Export de l'ontologie ---
  exportTtl = () =>
    this.http.get(`${API}/export.ttl`, {
      responseType: 'blob'
    });

  // --- CRUD par module ---
  classes = (m: string) =>
    this.http.get<OClass[]>(`${API}/${m}/classes`);

  createClass = (m: string, b: any) =>
    this.http.post(`${API}/${m}/classes`, b);

  updateClass = (m: string, n: string, b: any) =>
    this.http.put(`${API}/${m}/classes/${n}`, b);

  deleteClass = (m: string, n: string) =>
    this.http.delete(`${API}/${m}/classes/${n}`);

  classProps = (m: string, n: string) =>
    this.http.get<string[]>(
      `${API}/${m}/classes/${n}/properties`
    );

  items = (m: string, cls: string, columns: string[] = []) =>
    this.http.get<Individual[]>(
      `${API}/${m}/classes/${cls}/items`,
      { params: { columns: columns.join(',') } }
    );

  item = (m: string, id: string) =>
    this.http.get<Detail>(`${API}/${m}/items/${id}`);

  createItem = (m: string, b: any) =>
    this.http.post(`${API}/${m}/items`, b);

  updateItem = (m: string, id: string, b: any) =>
    this.http.put(`${API}/${m}/items/${id}`, b);

  deleteItem = (m: string, id: string) =>
    this.http.delete(`${API}/${m}/items/${id}`);

  // --- CRUD des propriétés ---
  props = () =>
    this.http.get<Prop[]>(`${API}/properties`);

  createProp = (b: any) =>
    this.http.post(`${API}/properties`, b);

  updateProp = (n: string, b: any) =>
    this.http.put(`${API}/properties/${n}`, b);

  deleteProp = (n: string) =>
    this.http.delete(`${API}/properties/${n}`);
}
