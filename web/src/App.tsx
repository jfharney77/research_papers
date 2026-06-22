import { useEffect, useMemo, useState } from "react";
import "./App.css";
import { fetchTemplates, type TemplateInfo } from "./api";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

const FALLBACK_TEMPLATES: TemplateInfo[] = [{ id: "ieee", name: "IEEE", buildable: true }];
const FALLBACK_DEFAULT = "ieee";

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

function App() {
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [templates, setTemplates] = useState<TemplateInfo[]>(FALLBACK_TEMPLATES);
  const [defaultTemplate, setDefaultTemplate] = useState<string>(FALLBACK_DEFAULT);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [view, setView] = useState<"pdf" | "latex" | "word" | "log">("pdf");
  const [activeSection, setActiveSection] = useState<string | null>(null);
  const [latexSource, setLatexSource] = useState<string>("Select a section to inspect its LaTeX.");
  const [buildLog, setBuildLog] = useState<string>("Select Log to view the LaTeX build output.");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [recompiling, setRecompiling] = useState(false);
  const [savingSection, setSavingSection] = useState(false);
  const [pendingOverwrite, setPendingOverwrite] = useState<{ file: File; template: string } | null>(null);

  const selected = useMemo(
    () => documents.find((doc) => doc.document_id === selectedId) ?? null,
    [documents, selectedId],
  );

  useEffect(() => {
    void refreshDocuments();
    void loadTemplates();
  }, []);

  async function loadTemplates() {
    try {
      const data = await fetchTemplates();
      if (data.templates?.length) {
        setTemplates(data.templates);
      }
      if (data.default) {
        setDefaultTemplate(data.default);
      }
    } catch (err) {
      console.error(err);
      setError("Failed to load templates; using defaults.");
    }
  }

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
    const template = (formData.get("template") as string) ?? defaultTemplate;
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
      setNotice(null);
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

  async function recompile(docId: string) {
    setRecompiling(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/documents/${docId}/compile`, { method: "POST" });
      if (!res.ok) {
        const detail = await res.json().catch(() => ({}));
        throw new Error(detail.detail ?? "Recompile failed");
      }
      await refreshDocuments();
      if (view === "log") {
        await loadBuildLog(docId);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Recompile failed");
    } finally {
      setRecompiling(false);
    }
  }

  async function loadBuildLog(docId: string) {
    setView("log");
    setBuildLog("Loading build log…");
    try {
      const res = await fetch(`${API_BASE}/documents/${docId}/log`);
      if (!res.ok) {
        setBuildLog(res.status === 404 ? "No build log available yet." : "Unable to load build log.");
        return;
      }
      setBuildLog(await res.text());
    } catch {
      setBuildLog("Unable to load build log.");
    }
  }

  async function saveSection() {
    if (!selected || !activeSection) return;
    setSavingSection(true);
    setError(null);
    setNotice(null);
    try {
      const res = await fetch(`${API_BASE}/documents/${selected.document_id}/sections/${activeSection}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: latexSource }),
      });
      if (!res.ok) {
        const detail = await res.json().catch(() => ({}));
        throw new Error(detail.detail ?? "Failed to save section");
      }
      setNotice("Section saved. Recompile to rebuild the PDF.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save section");
    } finally {
      setSavingSection(false);
    }
  }

  const pdfUrl = selected?.build.pdf_path ? `${API_BASE}/documents/${selected.document_id}/pdf` : null;
  const archiveUrl = selected ? `${API_BASE}/documents/${selected.document_id}/archive` : null;
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
            <select name="template" key={defaultTemplate} defaultValue={defaultTemplate}>
              {templates.map((tpl) => (
                <option
                  key={tpl.id}
                  value={tpl.id}
                  disabled={!tpl.buildable}
                  title={tpl.description ?? undefined}
                >
                  {tpl.name}
                  {tpl.buildable ? "" : " (build script missing)"}
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
      {notice && <div className="banner">{notice}</div>}

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
                  <p className="doc-meta">
                    Template · {selected.template.toUpperCase()} ·{" "}
                    <span className={`status ${selected.build.status}`}>build {selected.build.status}</span>
                  </p>
                </div>
                <div className="tab-bar">
                  {(["pdf", "latex", "word", "log"] as const).map((tab) => (
                    <button
                      key={tab}
                      className={view === tab ? "active" : ""}
                      onClick={() =>
                        tab === "log" ? void loadBuildLog(selected.document_id) : setView(tab)
                      }
                    >
                      {tab.toUpperCase()}
                    </button>
                  ))}
                  <button onClick={() => void recompile(selected.document_id)} disabled={recompiling}>
                    {recompiling ? "Recompiling…" : "↻ Recompile"}
                  </button>
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
                        {selected.build.status === "failed" ? (
                          <>
                            <p>{selected.build.message ?? "The LaTeX build failed."}</p>
                            <button onClick={() => void loadBuildLog(selected.document_id)}>
                              View build log
                            </button>
                          </>
                        ) : (
                          <p>No PDF build yet. Convert or recompile to generate one.</p>
                        )}
                      </div>
                    )
                  )}

                  {view === "latex" && (
                    <div className="latex-editor">
                      <div className="editor-toolbar">
                        <span>
                          {activeSection ? `Editing: ${activeSection}` : "Select a section to edit its LaTeX."}
                        </span>
                        <button onClick={() => void saveSection()} disabled={!activeSection || savingSection}>
                          {savingSection ? "Saving…" : "Save"}
                        </button>
                      </div>
                      <textarea
                        className="latex-view"
                        value={latexSource}
                        onChange={(e) => setLatexSource(e.target.value)}
                        readOnly={!activeSection}
                        spellCheck={false}
                      />
                    </div>
                  )}

                  {view === "log" && <pre className="latex-view">{buildLog}</pre>}

                  {view === "word" && (
                    <div className="word-view">
                      <p>Download the original manuscript or the generated LaTeX sources.</p>
                      {wordUrl && (
                        <a href={wordUrl} target="_blank" rel="noreferrer">
                          Download DOCX
                        </a>
                      )}
                      {archiveUrl && (
                        <a href={archiveUrl} target="_blank" rel="noreferrer">
                          Download LaTeX (.zip)
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
