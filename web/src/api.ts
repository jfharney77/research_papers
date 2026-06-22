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
