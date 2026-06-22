export const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

const TOKEN = import.meta.env.VITE_DOCSERVER_TOKEN ?? "";

/** Authorization header sent when a token is configured (matches DOCSERVER_API_KEY). */
export function authHeaders(): Record<string, string> {
  return TOKEN ? { Authorization: `Bearer ${TOKEN}` } : {};
}

/** Query suffix carrying the token, for browser GETs (PDF iframe, downloads). */
export function authParam(sep: "?" | "&" = "?"): string {
  return TOKEN ? `${sep}api_key=${encodeURIComponent(TOKEN)}` : "";
}

export type TemplateInfo = {
  id: string;
  name: string;
  description?: string | null;
  buildable: boolean;
};

export type TemplateListResponse = {
  templates: TemplateInfo[];
  default: string;
};

export async function fetchTemplates(): Promise<TemplateListResponse> {
  const res = await fetch(`${API_BASE}/templates`, { headers: authHeaders() });
  if (!res.ok) {
    throw new Error(`Failed to load templates (${res.status})`);
  }
  return res.json();
}

// --- Critic -----------------------------------------------------------------

export type Criticism = { category: string; issue: string; suggestion: string };

export type SectionCritique = {
  section_slug: string;
  title: string;
  criticisms: Criticism[];
  ai_score: number;
  ai_score_breakdown: { heuristic: number; model: number };
  ai_signals: string[];
  deai_tips: string[];
};

export type CritiqueResult = {
  document_id: string | null;
  provider: string;
  created_at: string;
  overall_ai_score: number;
  summary: string;
  sections: SectionCritique[];
};

export type ProviderListResponse = {
  providers: { id: string; available: boolean; active: boolean }[];
  active: string;
};

export async function fetchProviders(): Promise<ProviderListResponse> {
  const res = await fetch(`${API_BASE}/critic/providers`, { headers: authHeaders() });
  if (!res.ok) throw new Error(`Failed to load providers (${res.status})`);
  return res.json();
}

export async function fetchCritique(documentId: string): Promise<CritiqueResult | null> {
  const res = await fetch(`${API_BASE}/documents/${documentId}/critique`, { headers: authHeaders() });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`Failed to load critique (${res.status})`);
  return res.json();
}

export async function runCritique(documentId: string, refresh = false): Promise<CritiqueResult> {
  const res = await fetch(`${API_BASE}/documents/${documentId}/critique?refresh=${refresh}`, {
    method: "POST",
    headers: authHeaders(),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail ?? "Critique failed");
  }
  return res.json();
}

export async function critiqueAdhoc(file: File): Promise<CritiqueResult> {
  const payload = new FormData();
  payload.append("file", file);
  const res = await fetch(`${API_BASE}/critic/adhoc`, {
    method: "POST",
    headers: authHeaders(),
    body: payload,
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail ?? "Ad-hoc critique failed");
  }
  return res.json();
}
