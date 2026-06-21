const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

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
  const res = await fetch(`${API_BASE}/templates`);
  if (!res.ok) {
    throw new Error(`Failed to load templates (${res.status})`);
  }
  return res.json();
}
