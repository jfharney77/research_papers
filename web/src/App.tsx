import { useEffect, useMemo, useState } from "react";
import "./App.css";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

type BuildState = {
  status: "pending" | "succeeded" | "failed";
  pdf_path?: string | null;
  message?: string | null;
};

type Section = {
  section_id: string;
  title: string;
  level: number;
  slug: string;
  latex_path: string;
  order: number;
};

type DocumentRecord = {
  document_id: string;
  title: string;
  template: string;
  source_docx: string;
  created_at: string;
  sections: Section[];
  build: BuildState;
};

const TEMPLATE_CHOICES = ["ieee", "acm", "neurips", "aaai"];

function App() {
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [view, setView] = useState<"pdf" | "latex" | "word">("pdf");
  const [activeSection, setActiveSection] = useState<string | null>(null);
  const [latexSource, setLatexSource] = useState<string>("Select a section to inspect its LaTeX.");
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [pendingOverwrite, setPendingOverwrite] = useState<{ file: File; template: string } | null>(null);

  const selected = useMemo(
    () => documents.find((doc) => doc.document_id === selectedId) ?? null,
    [documents, selectedId],
  );

  useEffect(() => {
    void refreshDocuments();
  }, []);

  async function refreshDocuments() {
    try {
      const res = await fetch(`${API_BASE}/documents`);
      const data = await res.json();
      setDocuments(data.documents ?? []);
      if (!selectedId && data.documents?.length) {
        setSelectedId(data.documents[0].document_id);
      }
    } catch (err) {
      console.error(err);
      setError("Failed to load documents list.");
    }
  }

  async function handleUpload(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    if (!(formData.get("file") instanceof File)) {
      setError("Attach a .docx manuscript first.");
      return;
    }

    const file = formData.get("file") as File;
    const template = (formData.get("template") as string) ?? "ieee";
    await submitUpload(file, template, false, event.currentTarget);
  }

  async function submitUpload(file: File, template: string, overwrite: boolean, form?: HTMLFormElement) {
    const payload = new FormData();
    payload.append("file", file);
    payload.append("template", template);
    payload.append("build_pdf", "true");
    payload.append("overwrite", overwrite ? "true" : "false");

    setUploading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/documents?template=${encodeURIComponent(template)}&build_pdf=true&overwrite=${overwrite}`, {
        method: "POST",
        body: payload,
      });
      if (!res.ok) {
        const detail = await res.json().catch(() => ({}));
        const message = detail.detail ?? "Conversion failed";
        if (message.includes("already exists") && !overwrite) {
          setPendingOverwrite({ file, template });
          setError("Workspace exists. Overwrite?");
          return;
        }
        throw new Error(message);
      }
      form?.reset();
      setPendingOverwrite(null);
      await refreshDocuments();
    } catch (err) {
      if (!(err instanceof Error && err.message.includes("Workspace exists"))) {
        setError(err instanceof Error ? err.message : "Upload failed");
      }
    } finally {
      setUploading(false);
    }
  }

  async function loadSection(section: Section) {
    if (!selected) return;
    try {
      const res = await fetch(`${API_BASE}/documents/${selected.document_id}/sections/${section.slug}`);
      if (!res.ok) throw new Error("Unable to load section");
      const text = await res.text();
      setLatexSource(text);
      setActiveSection(section.slug);
      setView("latex");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load section");
    }
  }

  async function deleteSelected(docId: string) {
    if (!window.confirm("Delete this workspace? This cannot be undone.")) {
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/documents/${docId}`, { method: "DELETE" });
      if (!res.ok) {
        const detail = await res.json().catch(() => ({}));
        throw new Error(detail.detail ?? "Failed to delete workspace");
      }
      if (selectedId === docId) {
        setSelectedId(null);
        setActiveSection(null);
        setLatexSource("Select a section to inspect its LaTeX.");
      }
      await refreshDocuments();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete workspace");
    }
  }

  const pdfUrl = selected?.build.pdf_path ? `${API_BASE}/documents/${selected.document_id}/pdf` : null;
  const wordUrl = selected ? `${API_BASE}/documents/${selected.document_id}/word` : null;

  return (
    <div className="app-shell">
      <header className="masthead">
        <div>
          <p className="eyebrow">Research Paper Foundry</p>
          <h1>Word → LaTeX Command Center</h1>
          <p className="lede">
            Feed Word manuscripts, break them into venue-specific LaTeX sections, and keep PDFs, code, and
            originals in sync.
          </p>
        </div>
        <form className="upload-form" onSubmit={handleUpload}>
          <label>
            <span>Word document</span>
            <input name="file" type="file" accept=".docx" required />
          </label>
          <label>
            <span>Template</span>
            <select name="template" defaultValue="ieee">
              {TEMPLATE_CHOICES.map((tpl) => (
                <option key={tpl} value={tpl}>
                  {tpl.toUpperCase()}
                </option>
              ))}
            </select>
          </label>
          <button type="submit" disabled={uploading}>
            {uploading ? "Converting…" : "Convert"}
          </button>
        </form>
      </header>

      {error && <div className="banner error">{error}</div>}

      <div className="layout">
        <aside>
          <div className="aside-head">
            <h2>Workspace</h2>
            <button className="refresh" onClick={() => void refreshDocuments()}>
              ↻ Refresh
            </button>
          </div>
          {pendingOverwrite && (
            <div className="banner warning">
              <p>
                Workspace already exists. Replace it?
                <button
                  onClick={() => submitUpload(pendingOverwrite.file, pendingOverwrite.template, true)}
                  disabled={uploading}
                >
                  Yes, overwrite
                </button>
                <button onClick={() => setPendingOverwrite(null)}>No</button>
              </p>
            </div>
          )}
          <ul className="document-list">
            {documents.map((doc) => (
              <li
                key={doc.document_id}
                className={doc.document_id === selectedId ? "active" : ""}
                onClick={() => setSelectedId(doc.document_id)}
              >
                <div>
                  <p className="doc-title">{doc.title}</p>
                  <p className="doc-meta">
                    {doc.template.toUpperCase()} · {new Date(doc.created_at).toLocaleString()}
                  </p>
                </div>
                <span className={`status ${doc.build.status}`}>{doc.build.status}</span>
              </li>
            ))}
            {!documents.length && <li className="empty">Upload a docx to start building.</li>}
          </ul>
        </aside>

        <main>
          {selected ? (
            <>
              <div className="document-header">
                <div>
                  <h2>{selected.title}</h2>
                  <p className="doc-meta">Template · {selected.template.toUpperCase()}</p>
                </div>
                <div className="tab-bar">
                  {["pdf", "latex", "word"].map((tab) => (
                    <button
                      key={tab}
                      className={view === tab ? "active" : ""}
                      onClick={() => setView(tab as typeof view)}
                    >
                      {tab.toUpperCase()}
                    </button>
                  ))}
                  <button className="danger" onClick={() => deleteSelected(selected.document_id)}>
                    Delete
                  </button>
                </div>
              </div>

              <div className="workspace">
                <section className="section-tree">
                  <h3>Sections</h3>
                  <ol>
                    {selected.sections.map((section) => (
                      <li key={section.section_id}>
                        <button
                          className={activeSection === section.slug ? "active" : ""}
                          onClick={() => loadSection(section)}
                        >
                          {section.title}
                        </button>
                      </li>
                    ))}
                    {!selected.sections.length && <li>No sections detected yet.</li>}
                  </ol>
                </section>

                <section className="viewer">
                  {view === "pdf" && (
                    pdfUrl ? (
                      <iframe title="PDF preview" src={pdfUrl} />
                    ) : (
                      <div className="empty-state">
                        <p>No PDF build yet. Convert or recompile to generate one.</p>
                      </div>
                    )
                  )}

                  {view === "latex" && <pre className="latex-view">{latexSource}</pre>}

                  {view === "word" && (
                    <div className="word-view">
                      <p>Download the original manuscript to iterate in Word.</p>
                      {wordUrl && (
                        <a href={wordUrl} target="_blank" rel="noreferrer">
                          Download DOCX
                        </a>
                      )}
                    </div>
                  )}
                </section>
              </div>
            </>
          ) : (
            <div className="empty-state">
              <p>No documents yet. Upload a Word file to get started.</p>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}

export default App;
