// ─── Entity Types ─────────────────────────────────────────────────────────────

export interface EntityTypeConfig {
  label: string;
  color: string;
  bg: string;
  icon?: string;
}

export type EntityCategory =
  | 'GEOLOGY' | 'SPECIES' | 'PHENOMENON' | 'WORK' | 'EVENT'
  | 'CHEMICAL' | 'ANATOMY' | 'LAW_RULE' | 'PERIOD' | 'ASTRONOMY'
  | 'ARTIFACT' | 'PERSON' | 'LOCATION' | 'ORGANIZATION' | 'UNIVERSITY'
  | 'DISEASE' | 'MEDICAL_TERM' | 'TECHNOLOGY' | 'FIELD' | 'CONCEPT'
  | 'DATE' | 'OTHER' | 'MISC';

// ─── Library Item ─────────────────────────────────────────────────────────────

export interface LibraryItem {
  id: string;
  annotationId?: string;
  text: string;
  type: EntityCategory | string;
  label_ar?: string;
  root?: string;
  note?: string;
  source?: string;
  created_at?: string;
}

// ─── Analysis ─────────────────────────────────────────────────────────────────

export interface Root {
  word: string;
  root: string;
}

export interface Entity {
  text: string;
  label: string;
  score: number;
  start: number;
  end: number;
  roots: Root[];
}

export interface AnalysisResult {
  text: string;
  entities: Entity[];
  allRoots: Root[];
  mock: boolean;
}

// ─── Auth ─────────────────────────────────────────────────────────────────────

export interface AuthUser {
  id?: string;
  email?: string;
  isDemo?: boolean;
}

export interface AuthContextValue {
  user: AuthUser | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signInDemo: () => void;
  signOut: () => Promise<void>;
}
