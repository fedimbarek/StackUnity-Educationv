import { MODULES } from './modules';

/** Un onglet = une sous-entité du module (une classe de l'ontologie) avec ses colonnes et ses champs de formulaire. */
export interface EntityTab { title: string; cls: string; columns: string[]; fields: string[]; }
export interface ModuleConfig { id: string; title: string; icon: string; desc: string; root: string; tabs: EntityTab[]; }

export const tab = (title: string, cls: string, columns: string[], fields: string[]): EntityTab => ({ title, cls, columns, fields });
export const meta = (id: string) => MODULES.find(m => m.id === id)!;
export const humanize = (n: string) => n.replace(/([a-z])([A-Z])/g, '$1 $2').replace(/^./, c => c.toUpperCase());
