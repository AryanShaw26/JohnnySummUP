import {
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  Download,
  FileText,
  Info,
  RefreshCw,
  Sparkles,
} from "lucide-react";
import { useEffect, useState } from "react";
import { workspaceApi } from "../../services/workspaceApi";
import type {
  WorkspaceAnalysis,
  WorkspaceDocument,
  WorkspaceFinding,
} from "../../types/workspace";
import type { WorkspaceMeta } from "./WorkspaceConfig";

interface Props {
  meta: WorkspaceMeta;
  documentId: string;
  onBack: () => void;
}

export function WorkspaceDocumentDetail({ meta, documentId, onBack }: Props) {
  const [doc, setDoc] = useState<WorkspaceDocument | null>(null);
  const [analysis, setAnalysis] = useState<WorkspaceAnalysis | null>(null);
  const [findings, setFindings] = useState<WorkspaceFinding[]>([]);
  const [activeTab, setActiveTab] = useState<"summary" | "findings" | "domain" | "raw">("summary");
  const [loading, setLoading] = useState(true);
  const [retrying, setRetrying] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchDetails = async () => {
    setLoading(true);
    setError(null);
    try {
      const docData = await workspaceApi.getDocument(meta.backendSlug, documentId);
      setDoc(docData);

      try {
        const analysisData = await workspaceApi.getAnalysis(meta.backendSlug, documentId);
        setAnalysis(analysisData);
      } catch {
        setAnalysis(null);
      }

      try {
        const findingsData = await workspaceApi.getFindings(meta.backendSlug, documentId);
        setFindings(findingsData);
      } catch {
        setFindings([]);
      }
    } catch (err: any) {
      setError(err?.message || "Failed to load document details.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDetails();
  }, [meta.backendSlug, documentId]);

  const handleRetry = async () => {
    setRetrying(true);
    try {
      await workspaceApi.retryAnalysis(meta.backendSlug, documentId);
      await fetchDetails();
    } catch (err: any) {
      alert(err?.message || "Retry failed.");
    } finally {
      setRetrying(false);
    }
  };

  const handleReviewToggle = async (findingId: string, currentStatus: string) => {
    const newStatus = currentStatus === "reviewed" ? "pending" : "reviewed";
    try {
      await workspaceApi.updateFinding(meta.backendSlug, documentId, findingId, {
        review_status: newStatus,
        is_reviewed: newStatus === "reviewed",
      });
      setFindings((prev) =>
        prev.map((f) =>
          f.id === findingId
            ? { ...f, review_status: newStatus as any, is_reviewed: newStatus === "reviewed" }
            : f
        )
      );
    } catch (err: any) {
      alert("Failed to update finding status.");
    }
  };

  if (loading) {
    return (
      <div className="card" style={{ textAlign: "center", padding: 60 }}>
        <RefreshCw size={26} className="spin" style={{ color: "var(--purple)", margin: "0 auto 12px" }} />
        <p style={{ color: "var(--muted)", margin: 0 }}>Loading document analysis...</p>
      </div>
    );
  }

  if (error || !doc) {
    return (
      <div className="card" style={{ borderColor: "#fca5a5", background: "#fff5f5", padding: 24 }}>
        <button
          onClick={onBack}
          className="text-link"
          style={{ background: "none", border: "none", cursor: "pointer", marginBottom: 12 }}
        >
          <ArrowLeft size={16} /> Back to documents
        </button>
        <p style={{ color: "#991b1b", fontWeight: 700 }}>{error || "Document not found."}</p>
      </div>
    );
  }

  const structured = analysis?.structured_data || {};

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {/* Top Header Card */}
      <div className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 12 }}>
          <div>
            <button
              onClick={onBack}
              className="text-link"
              style={{ background: "none", border: "none", cursor: "pointer", marginBottom: 8 }}
            >
              <ArrowLeft size={14} /> Back to all documents
            </button>
            <h2 style={{ fontSize: 22, margin: "0 0 6px", color: "var(--ink)" }}>
              {doc.label || doc.original_filename}
            </h2>
            <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
              <span className="pill pill--muted" style={{ textTransform: "capitalize" }}>
                {doc.document_subtype || doc.document_type}
              </span>
              <span style={{ fontSize: 12, color: "var(--muted)" }}>
                {doc.page_count} pages • {(doc.file_size_bytes / (1024 * 1024)).toFixed(2)} MB • Uploaded on {new Date(doc.created_at).toLocaleDateString()}
              </span>
              <span className={`badge-status badge-status--${doc.status}`}>
                {doc.status}
              </span>
            </div>
          </div>

          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            {doc.status === "failed" && (
              <button
                className="button button--compact button--primary"
                onClick={handleRetry}
                disabled={retrying}
              >
                <RefreshCw size={14} className={retrying ? "spin" : ""} /> Retry Analysis
              </button>
            )}
            <a
              href={workspaceApi.getDownloadUrl(meta.backendSlug, doc.id)}
              target="_blank"
              rel="noreferrer"
              className="button button--compact button--quiet"
              style={{ border: "1px solid var(--border)" }}
            >
              <Download size={14} /> Original File
            </a>
          </div>
        </div>

        {/* Failure alert banner */}
        {doc.status === "failed" && (
          <div
            style={{
              marginTop: 16,
              padding: "12px 16px",
              background: "#fee2e2",
              border: "1px solid #fca5a5",
              borderRadius: 8,
              color: "#991b1b",
              fontSize: 13,
            }}
          >
            <strong>Extraction / Analysis Failure:</strong> {doc.failure_message || "Processing could not be completed."} (Code: {doc.failure_code || "UNKNOWN"})
          </div>
        )}
      </div>

      {/* Navigation Tabs */}
      <div className="workspace-nav-bar" style={{ padding: "6px 12px" }}>
        <div className="workspace-nav-tabs">
          <button
            className={`workspace-nav-tab ${activeTab === "summary" ? "workspace-nav-tab--active" : ""}`}
            onClick={() => setActiveTab("summary")}
          >
            <Sparkles size={15} /> Summary & Key Points
          </button>
          <button
            className={`workspace-nav-tab ${activeTab === "findings" ? "workspace-nav-tab--active" : ""}`}
            onClick={() => setActiveTab("findings")}
          >
            <AlertTriangle size={15} /> Review Flags ({findings.length})
          </button>
          <button
            className={`workspace-nav-tab ${activeTab === "domain" ? "workspace-nav-tab--active" : ""}`}
            onClick={() => setActiveTab("domain")}
          >
            <FileText size={15} /> Structured {meta.name} Terms
          </button>
          <button
            className={`workspace-nav-tab ${activeTab === "raw" ? "workspace-nav-tab--active" : ""}`}
            onClick={() => setActiveTab("raw")}
          >
            <Info size={15} /> Extracted Text
          </button>
        </div>
      </div>

      {/* Tab 1: Summary & Key Points */}
      {activeTab === "summary" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div className="card">
            <h3 className="card__title" style={{ marginBottom: 12 }}>
              <Sparkles size={18} style={{ color: meta.accentColor }} /> Plain-Language Overview
            </h3>
            <p style={{ fontSize: 14.5, lineHeight: 1.6, color: "#2d2640", margin: "0 0 16px" }}>
              {analysis?.summary || doc.failure_message || "Document is awaiting analysis or processing was incomplete."}
            </p>

            {analysis?.key_points && analysis.key_points.length > 0 && (
              <div style={{ borderTop: "1px solid #f1ecf7", paddingTop: 14 }}>
                <strong style={{ fontSize: 13, color: "var(--ink)", display: "block", marginBottom: 8 }}>
                  Key Highlights & Takeaways
                </strong>
                <ul style={{ margin: 0, paddingLeft: 20, display: "flex", flexDirection: "column", gap: 6 }}>
                  {analysis.key_points.map((pt, i) => (
                    <li key={i} style={{ fontSize: 13.5, color: "#4f4765" }}>
                      {pt}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* Disclaimer pill */}
          {structured.disclaimer && (
            <div
              style={{
                padding: "10px 14px",
                background: "#fbf9fe",
                border: "1px solid #ede5f8",
                borderRadius: 10,
                fontSize: 12,
                color: "#6b5f84",
                display: "flex",
                alignItems: "center",
                gap: 8,
              }}
            >
              <Info size={14} style={{ color: meta.accentColor, flexShrink: 0 }} />
              <span>{structured.disclaimer}</span>
            </div>
          )}
        </div>
      )}

      {/* Tab 2: Findings & Hidden Details with Page Evidence */}
      {activeTab === "findings" && (
        <div className="card">
          <div className="card__header">
            <h3 className="card__title">
              <AlertTriangle size={18} style={{ color: "#b45309" }} /> Important Review Flags & Evidence
            </h3>
            <span style={{ fontSize: 12, color: "var(--muted)" }}>
              {findings.filter((f) => f.is_reviewed).length} of {findings.length} reviewed
            </span>
          </div>

          {findings.length === 0 ? (
            <p style={{ color: "var(--muted)", margin: 0, padding: "24px 0", textAlign: "center" }}>
              No critical review flags or unusual terms were identified in this document.
            </p>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {findings.map((f) => (
                <div key={f.id} className="finding-card" style={{ opacity: f.is_reviewed ? 0.65 : 1 }}>
                  <div className="finding-card__header">
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <span className={`badge-priority badge-priority--${f.review_priority}`}>
                        {f.review_priority}
                      </span>
                      <h4 className="finding-card__title">{f.title}</h4>
                    </div>

                    <button
                      className="button button--compact button--quiet"
                      style={{
                        fontSize: 11,
                        padding: "4px 8px",
                        border: "1px solid #e2dcf0",
                        color: f.is_reviewed ? "#059669" : "var(--muted)",
                      }}
                      onClick={() => handleReviewToggle(f.id, f.review_status)}
                    >
                      <CheckCircle2 size={13} />
                      {f.is_reviewed ? "Reviewed" : "Mark as Reviewed"}
                    </button>
                  </div>

                  <p className="finding-card__body">{f.explanation}</p>

                  {f.why_it_matters && (
                    <div className="finding-card__why">
                      <strong>Why this matters:</strong> {f.why_it_matters}
                    </div>
                  )}

                  {f.source_excerpt && (
                    <div className="finding-card__evidence">
                      <FileText size={14} style={{ color: meta.accentColor, flexShrink: 0, marginTop: 2 }} />
                      <div>
                        {f.source_page && (
                          <span style={{ fontWeight: 700, color: meta.accentColor, marginRight: 6 }}>
                            [Page {f.source_page}]:
                          </span>
                        )}
                        "{f.source_excerpt}"
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab 3: Structured Domain Data */}
      {activeTab === "domain" && (
        <div className="card">
          <h3 className="card__title" style={{ marginBottom: 16 }}>
            <FileText size={18} style={{ color: meta.accentColor }} /> Structured {meta.name} Information
          </h3>

          {/* Legal Render */}
          {meta.slug === "legal" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              {structured.parties && structured.parties.length > 0 && (
                <div>
                  <strong style={{ fontSize: 13, color: "var(--muted)", textTransform: "uppercase" }}>Parties</strong>
                  <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginTop: 6 }}>
                    {structured.parties.map((p: any, i: number) => (
                      <span key={i} className="pill">
                        <strong>{p.name}</strong> {p.role && `(${p.role})`}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
                <div style={{ background: "#fbf9fe", padding: 14, borderRadius: 10 }}>
                  <strong style={{ fontSize: 12, color: "var(--muted)" }}>GOVERNING JURISDICTION</strong>
                  <p style={{ margin: "4px 0 0", fontSize: 14, fontWeight: 700 }}>
                    {structured.governing_law || "Not explicitly specified"}
                  </p>
                  {structured.jurisdiction && (
                    <p style={{ margin: "2px 0 0", fontSize: 12, color: "var(--muted)" }}>
                      Court: {structured.jurisdiction}
                    </p>
                  )}
                </div>

                <div style={{ background: "#fbf9fe", padding: 14, borderRadius: 10 }}>
                  <strong style={{ fontSize: 12, color: "var(--muted)" }}>RENEWAL & NOTICE</strong>
                  <p style={{ margin: "4px 0 0", fontSize: 14, fontWeight: 700 }}>
                    {structured.renewal?.automatic_renewal ? "Automatic Renewal: YES" : "Standard Expiration"}
                  </p>
                  {structured.renewal?.notice_window && (
                    <p style={{ margin: "2px 0 0", fontSize: 12, color: "var(--muted)" }}>
                      Notice Window: {structured.renewal.notice_window}
                    </p>
                  )}
                </div>
              </div>

              {structured.obligations && structured.obligations.length > 0 && (
                <div>
                  <strong style={{ fontSize: 13, color: "var(--muted)", textTransform: "uppercase" }}>Key Obligations</strong>
                  <div style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: 8 }}>
                    {structured.obligations.map((ob: any, i: number) => (
                      <div key={i} style={{ padding: "8px 12px", border: "1px solid #f0eaf7", borderRadius: 8 }}>
                        <span style={{ fontWeight: 700, color: "var(--ink)", marginRight: 8 }}>{ob.party}:</span>
                        <span style={{ color: "#4f4765" }}>{ob.description}</span>
                        {ob.deadline && <span style={{ marginLeft: 8, color: "var(--purple)", fontSize: 12 }}>({ob.deadline})</span>}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Finance Render */}
          {meta.slug === "finance" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12 }}>
                <div style={{ background: "#fbf9fe", padding: 12, borderRadius: 10 }}>
                  <span style={{ fontSize: 11, color: "var(--muted)", textTransform: "uppercase" }}>Opening Balance</span>
                  <p style={{ margin: "4px 0 0", fontSize: 20, fontWeight: 800 }}>
                    {structured.currency || "$"} {structured.opening_balance ?? "N/A"}
                  </p>
                </div>
                <div style={{ background: "#fbf9fe", padding: 12, borderRadius: 10 }}>
                  <span style={{ fontSize: 11, color: "var(--muted)", textTransform: "uppercase" }}>Closing Balance</span>
                  <p style={{ margin: "4px 0 0", fontSize: 20, fontWeight: 800, color: "#059669" }}>
                    {structured.currency || "$"} {structured.closing_balance ?? "N/A"}
                  </p>
                </div>
                <div style={{ background: "#fbf9fe", padding: 12, borderRadius: 10 }}>
                  <span style={{ fontSize: 11, color: "var(--muted)", textTransform: "uppercase" }}>Total Debits</span>
                  <p style={{ margin: "4px 0 0", fontSize: 20, fontWeight: 800, color: "#b91c1c" }}>
                    {structured.currency || "$"} {structured.total_debits ?? "N/A"}
                  </p>
                </div>
                <div style={{ background: "#fbf9fe", padding: 12, borderRadius: 10 }}>
                  <span style={{ fontSize: 11, color: "var(--muted)", textTransform: "uppercase" }}>Total Credits</span>
                  <p style={{ margin: "4px 0 0", fontSize: 20, fontWeight: 800, color: "#2563eb" }}>
                    {structured.currency || "$"} {structured.total_credits ?? "N/A"}
                  </p>
                </div>
              </div>

              {structured.transactions && structured.transactions.length > 0 && (
                <div>
                  <strong style={{ fontSize: 13, color: "var(--muted)", textTransform: "uppercase" }}>Transactions</strong>
                  <table className="workspace-table" style={{ marginTop: 8 }}>
                    <thead>
                      <tr>
                        <th>Date</th>
                        <th>Description</th>
                        <th>Type</th>
                        <th style={{ textAlign: "right" }}>Amount</th>
                      </tr>
                    </thead>
                    <tbody>
                      {structured.transactions.map((t: any, i: number) => (
                        <tr key={i}>
                          <td>{t.date || "—"}</td>
                          <td>{t.description}</td>
                          <td>
                            <span className="pill pill--muted" style={{ padding: "2px 8px", fontSize: 10 }}>
                              {t.transaction_type}
                            </span>
                          </td>
                          <td style={{ textAlign: "right", fontWeight: 700 }}>
                            {t.amount != null ? `${structured.currency || "$"} ${Number(t.amount).toFixed(2)}` : "—"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* Insurance Render */}
          {meta.slug === "insurance" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
                <div style={{ background: "#fbf9fe", padding: 14, borderRadius: 10 }}>
                  <span style={{ fontSize: 11, color: "var(--muted)", textTransform: "uppercase" }}>Sum Insured</span>
                  <p style={{ margin: "4px 0 0", fontSize: 18, fontWeight: 800 }}>{structured.sum_insured || "Not stated"}</p>
                </div>
                <div style={{ background: "#fbf9fe", padding: 14, borderRadius: 10 }}>
                  <span style={{ fontSize: 11, color: "var(--muted)", textTransform: "uppercase" }}>Deductibles & Co-pay</span>
                  <p style={{ margin: "4px 0 0", fontSize: 15, fontWeight: 700 }}>{structured.deductibles_and_copay || "Standard terms"}</p>
                </div>
              </div>

              {structured.coverages && structured.coverages.length > 0 && (
                <div>
                  <strong style={{ fontSize: 13, color: "var(--muted)", textTransform: "uppercase" }}>Coverages</strong>
                  <table className="workspace-table" style={{ marginTop: 8 }}>
                    <thead>
                      <tr>
                        <th>Benefit / Item</th>
                        <th>Limit</th>
                        <th>Deductible</th>
                      </tr>
                    </thead>
                    <tbody>
                      {structured.coverages.map((c: any, i: number) => (
                        <tr key={i}>
                          <td><strong>{c.name}</strong></td>
                          <td>{c.limit || "—"}</td>
                          <td>{c.deductible || "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {structured.exclusions && structured.exclusions.length > 0 && (
                <div>
                  <strong style={{ fontSize: 13, color: "var(--muted)", textTransform: "uppercase" }}>Exclusions</strong>
                  <div style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: 8 }}>
                    {structured.exclusions.map((ex: any, i: number) => (
                      <div key={i} style={{ padding: "10px 12px", border: "1px solid #fee2e2", borderRadius: 8, background: "#fffdfd" }}>
                        <strong style={{ color: "#991b1b" }}>{ex.title}</strong>
                        <p style={{ margin: "4px 0 0", fontSize: 13, color: "#7f1d1d" }}>{ex.explanation}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Education Render */}
          {meta.slug === "education" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
                <div style={{ background: "#fbf9fe", padding: 14, borderRadius: 10 }}>
                  <span style={{ fontSize: 11, color: "var(--muted)", textTransform: "uppercase" }}>Reported GPA / Result</span>
                  <p style={{ margin: "4px 0 0", fontSize: 20, fontWeight: 800 }}>{structured.reported_gpa || "N/A"}</p>
                </div>
                <div style={{ background: "#fbf9fe", padding: 14, borderRadius: 10 }}>
                  <span style={{ fontSize: 11, color: "var(--muted)", textTransform: "uppercase" }}>Credits Earned</span>
                  <p style={{ margin: "4px 0 0", fontSize: 20, fontWeight: 800 }}>{structured.total_credits_earned ?? "N/A"}</p>
                </div>
              </div>

              {structured.courses_and_subjects && structured.courses_and_subjects.length > 0 && (
                <div>
                  <strong style={{ fontSize: 13, color: "var(--muted)", textTransform: "uppercase" }}>Courses & Grades</strong>
                  <table className="workspace-table" style={{ marginTop: 8 }}>
                    <thead>
                      <tr>
                        <th>Code</th>
                        <th>Subject Name</th>
                        <th>Credits</th>
                        <th>Grade</th>
                      </tr>
                    </thead>
                    <tbody>
                      {structured.courses_and_subjects.map((c: any, i: number) => (
                        <tr key={i}>
                          <td><code>{c.code || "—"}</code></td>
                          <td><strong>{c.name}</strong></td>
                          <td>{c.credits ?? "—"}</td>
                          <td><span className="pill pill--muted">{c.grade || "—"}</span></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* Employment & Government Render */}
          {meta.slug === "employment-government" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
                <div style={{ background: "#fbf9fe", padding: 14, borderRadius: 10 }}>
                  <span style={{ fontSize: 11, color: "var(--muted)", textTransform: "uppercase" }}>Gross Salary / Compensation</span>
                  <p style={{ margin: "4px 0 0", fontSize: 18, fontWeight: 800 }}>
                    {structured.compensation?.gross_salary || "Not stated"}
                  </p>
                </div>
                <div style={{ background: "#fbf9fe", padding: 14, borderRadius: 10 }}>
                  <span style={{ fontSize: 11, color: "var(--muted)", textTransform: "uppercase" }}>Notice Period</span>
                  <p style={{ margin: "4px 0 0", fontSize: 15, fontWeight: 700 }}>
                    {structured.notice_period || "Standard company policy"}
                  </p>
                </div>
              </div>

              {structured.restrictive_covenants && structured.restrictive_covenants.length > 0 && (
                <div>
                  <strong style={{ fontSize: 13, color: "var(--muted)", textTransform: "uppercase" }}>Restrictive Covenants</strong>
                  <div style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: 8 }}>
                    {structured.restrictive_covenants.map((rc: any, i: number) => (
                      <div key={i} style={{ padding: "10px 12px", border: "1px solid #fee2e2", borderRadius: 8, background: "#fffdfd" }}>
                        <strong style={{ color: "#991b1b" }}>{rc.clause_title}</strong>
                        <p style={{ margin: "4px 0 0", fontSize: 13, color: "#7f1d1d" }}>{rc.description}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Tab 4: Raw Extracted Text */}
      {activeTab === "raw" && (
        <div className="card">
          <h3 className="card__title" style={{ marginBottom: 12 }}>
            <FileText size={18} style={{ color: meta.accentColor }} /> Extracted Document Text
          </h3>
          <pre
            style={{
              background: "#faf9fd",
              border: "1px solid var(--border)",
              borderRadius: 10,
              padding: 16,
              fontSize: 12.5,
              lineHeight: 1.5,
              whiteSpace: "pre-wrap",
              wordBreak: "break-word",
              maxHeight: 500,
              overflowY: "auto",
              color: "#332c44",
            }}
          >
            {analysis?.extracted_text || "No text available."}
          </pre>
        </div>
      )}
    </div>
  );
}
