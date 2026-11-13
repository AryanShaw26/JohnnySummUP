import {
  AlertTriangle,
  ArrowRight,
  Calendar,
  FileText,
  Plus,
  RefreshCw,
  Sparkles,
} from "lucide-react";
import { useEffect, useState } from "react";
import { workspaceApi } from "../../services/workspaceApi";
import type { WorkspaceOverview as WorkspaceOverviewType } from "../../types/workspace";
import type { WorkspaceMeta } from "./WorkspaceConfig";

interface Props {
  meta: WorkspaceMeta;
  onNavigateTab: (tab: string) => void;
  onSelectDoc: (id: string) => void;
}

export function WorkspaceOverview({ meta, onNavigateTab, onSelectDoc }: Props) {
  const [data, setData] = useState<WorkspaceOverviewType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchOverview = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await workspaceApi.getOverview(meta.backendSlug);
      setData(res);
    } catch (err: any) {
      setError(err?.message || "Failed to load workspace overview.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOverview();
  }, [meta.backendSlug]);

  if (loading) {
    return (
      <div className="card" style={{ textAlign: "center", padding: 48 }}>
        <RefreshCw size={24} className="spin" style={{ color: "var(--purple)", margin: "0 auto 12px" }} />
        <p style={{ color: "var(--muted)", margin: 0 }}>Loading {meta.name} workspace metrics...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card" style={{ borderColor: "#fca5a5", background: "#fff5f5" }}>
        <p style={{ color: "#b91c1c", fontWeight: 600, margin: "0 0 10px" }}>{error}</p>
        <button className="button button--compact button--primary" onClick={fetchOverview}>
          <RefreshCw size={14} /> Retry
        </button>
      </div>
    );
  }

  const overview = data || {
    workspace: meta.backendSlug,
    total_documents: 0,
    completed_documents: 0,
    failed_documents: 0,
    pending_documents: 0,
    subtypes_breakdown: {},
    recent_documents: [],
    urgent_findings: [],
    deadlines: [],
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      {/* Top Banner */}
      <div
        style={{
          background: "linear-gradient(135deg, #ffffff 0%, #f7f4fd 100%)",
          border: "1px solid var(--border)",
          borderRadius: 16,
          padding: "24px 28px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: 16,
        }}
      >
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
            <span
              className="workspace-header-badge"
              style={{ background: "#ede4fc", color: meta.accentColor }}
            >
              {meta.name}
            </span>
            <span style={{ fontSize: 13, color: "var(--muted)" }}>Official Workspace</span>
          </div>
          <h2 style={{ fontSize: 22, margin: 0, color: "var(--ink)" }}>{meta.tagline}</h2>
          <div style={{ display: "flex", gap: 16, flexWrap: "wrap", marginTop: 10 }}>
            {meta.sampleTips.map((tip, i) => (
              <span key={i} style={{ fontSize: 12, color: "#5d5475", display: "inline-flex", alignItems: "center", gap: 5 }}>
                <Sparkles size={12} style={{ color: meta.accentColor }} /> {tip}
              </span>
            ))}
          </div>
        </div>

        <button
          className="button button--primary button--large"
          onClick={() => onNavigateTab("upload")}
        >
          <Plus size={18} /> Upload Document
        </button>
      </div>

      {/* KPI Cards */}
      <div className="kpi-grid">
        <div className="kpi-card">
          <span className="kpi-card__label">Total Documents</span>
          <span className="kpi-card__value">{overview.total_documents}</span>
        </div>
        <div className="kpi-card">
          <span className="kpi-card__label">Analyses Completed</span>
          <span className="kpi-card__value" style={{ color: "#059669" }}>
            {overview.completed_documents}
          </span>
        </div>
        <div className="kpi-card">
          <span className="kpi-card__label">Action Flags / Warnings</span>
          <span className="kpi-card__value" style={{ color: overview.urgent_findings.length > 0 ? "#b45309" : "var(--ink)" }}>
            {overview.urgent_findings.length}
          </span>
        </div>
        <div className="kpi-card">
          <span className="kpi-card__label">Upcoming Deadlines</span>
          <span className="kpi-card__value" style={{ color: overview.deadlines.length > 0 ? "#7136d8" : "var(--ink)" }}>
            {overview.deadlines.length}
          </span>
        </div>
      </div>

      {/* Main 2-column layout */}
      <div style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr", gap: 20 }}>
        {/* Left Column: Recent Documents */}
        <div className="card">
          <div className="card__header">
            <h3 className="card__title">
              <FileText size={18} style={{ color: meta.accentColor }} /> Recent Documents
            </h3>
            <button
              onClick={() => onNavigateTab("documents")}
              className="text-link"
              style={{ background: "none", border: "none", cursor: "pointer" }}
            >
              View all ({overview.total_documents}) <ArrowRight size={14} />
            </button>
          </div>

          {overview.recent_documents.length === 0 ? (
            <div style={{ textAlign: "center", padding: "36px 12px" }}>
              <FileText size={32} style={{ color: "#cfc6ea", margin: "0 auto 10px" }} />
              <p style={{ color: "var(--muted)", margin: "0 0 12px", fontSize: 14 }}>
                No documents uploaded in {meta.name} yet.
              </p>
              <button
                className="button button--compact button--primary"
                onClick={() => onNavigateTab("upload")}
              >
                Upload your first document
              </button>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {overview.recent_documents.map((doc) => (
                <div
                  key={doc.id}
                  onClick={() => onSelectDoc(doc.id)}
                  style={{
                    padding: "12px 14px",
                    border: "1px solid #f1ecf7",
                    borderRadius: 10,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    cursor: "pointer",
                    transition: "all 0.15s ease",
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = "#faf8fd")}
                  onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                >
                  <div style={{ minWidth: 0 }}>
                    <p style={{ margin: "0 0 4px", fontWeight: 700, fontSize: 14, color: "var(--ink)" }}>
                      {doc.label || doc.original_filename}
                    </p>
                    <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                      <span className="pill pill--muted" style={{ padding: "2px 8px", fontSize: 10 }}>
                        {doc.document_subtype || doc.document_type}
                      </span>
                      <span style={{ fontSize: 11, color: "var(--muted)" }}>
                        {new Date(doc.created_at).toLocaleDateString()}
                      </span>
                    </div>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <span className={`badge-status badge-status--${doc.status}`}>
                      {doc.status}
                    </span>
                    <ArrowRight size={14} style={{ color: "#9c94b2" }} />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right Column: Urgent Flags & Deadlines */}
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          {/* Urgent Flags */}
          <div className="card">
            <div className="card__header">
              <h3 className="card__title">
                <AlertTriangle size={18} style={{ color: "#b45309" }} /> Important Findings
              </h3>
              <button
                onClick={() => onNavigateTab("findings")}
                className="text-link"
                style={{ background: "none", border: "none", cursor: "pointer" }}
              >
                All <ArrowRight size={14} />
              </button>
            </div>

            {overview.urgent_findings.length === 0 ? (
              <p style={{ color: "var(--muted)", margin: 0, fontSize: 13, textAlign: "center", padding: "16px 0" }}>
                No critical review flags detected in this workspace.
              </p>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {overview.urgent_findings.slice(0, 3).map((f) => (
                  <div
                    key={f.id}
                    onClick={() => onSelectDoc(f.document_id)}
                    style={{
                      padding: "10px 12px",
                      borderRadius: 8,
                      border: "1px solid #fef3c7",
                      background: "#fffdfa",
                      cursor: "pointer",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
                      <strong style={{ fontSize: 13, color: "#92400e" }}>{f.title}</strong>
                      <span className={`badge-priority badge-priority--${f.review_priority}`}>
                        {f.review_priority}
                      </span>
                    </div>
                    <p style={{ margin: 0, fontSize: 12, color: "#78350f", lineHeight: 1.4 }}>
                      {f.explanation}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Deadlines Checklist Preview */}
          <div className="card">
            <div className="card__header">
              <h3 className="card__title">
                <Calendar size={18} style={{ color: meta.accentColor }} /> Action Checklist
              </h3>
              <button
                onClick={() => onNavigateTab("checklist")}
                className="text-link"
                style={{ background: "none", border: "none", cursor: "pointer" }}
              >
                All <ArrowRight size={14} />
              </button>
            </div>

            {overview.deadlines.length === 0 ? (
              <p style={{ color: "var(--muted)", margin: 0, fontSize: 13, textAlign: "center", padding: "16px 0" }}>
                No active deadline obligations found.
              </p>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {overview.deadlines.slice(0, 3).map((d) => (
                  <div
                    key={d.id}
                    onClick={() => onSelectDoc(d.document_id)}
                    style={{
                      padding: "8px 12px",
                      borderRadius: 8,
                      background: "#fbf9fe",
                      border: "1px solid #f0eaf7",
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                    }}
                  >
                    <span style={{ fontSize: 13, fontWeight: 600, color: "var(--ink)" }}>{d.title}</span>
                    <span style={{ fontSize: 11, color: "var(--purple)", fontWeight: 700 }}>
                      Page {d.source_page || "1"}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
