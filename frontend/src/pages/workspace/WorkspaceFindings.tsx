import React, { useEffect, useState } from "react";
import { AlertCircle, AlertTriangle, CheckCircle, Info, RefreshCw } from "lucide-react";
import type { WorkspaceFinding } from "../../types/workspace";
import { workspaceApi } from "../../services/workspaceApi";
import type { WorkspaceMeta } from "./WorkspaceConfig";

interface Props {
  meta: WorkspaceMeta;
  onSelectDoc?: (docId: string) => void;
}

export const WorkspaceFindings: React.FC<Props> = ({ meta, onSelectDoc }) => {
  const [findings, setFindings] = useState<WorkspaceFinding[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [priorityFilter, setPriorityFilter] = useState<"all" | "high" | "review" | "info">("all");
  const [statusFilter, setStatusFilter] = useState<"all" | "pending" | "reviewed">("all");
  const [updatingId, setUpdatingId] = useState<string | null>(null);

  const fetchFindings = async () => {
    try {
      setLoading(true);
      setError(null);
      const items = await workspaceApi.getWorkspaceFindings(meta.backendSlug, {
        priority: priorityFilter === "all" ? undefined : priorityFilter,
        is_reviewed: statusFilter === "all" ? undefined : statusFilter === "reviewed",
      });
      setFindings(items);
    } catch (err: any) {
      setError(err?.message || "Failed to load findings");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFindings();
  }, [meta.backendSlug, priorityFilter, statusFilter]);

  const handleToggleReviewed = async (finding: WorkspaceFinding) => {
    try {
      setUpdatingId(finding.id);
      const updated = await workspaceApi.updateWorkspaceFinding(meta.backendSlug, finding.id, {
        is_reviewed: !finding.is_reviewed,
      });
      setFindings((prev) => prev.map((f) => (f.id === updated.id ? updated : f)));
    } catch (err: any) {
      alert(`Could not update finding status: ${err?.message || "Network error"}`);
    } finally {
      setUpdatingId(null);
    }
  };

  return (
    <div className="workspace-findings-view">
      <div className="workspace-card" style={{ marginBottom: "1.25rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "1rem" }}>
          <div>
            <h3 style={{ margin: 0, fontSize: "1.25rem", color: "#0f172a" }}>Workspace Findings & Evidence</h3>
            <p style={{ margin: "0.25rem 0 0 0", color: "#64748b", fontSize: "0.875rem" }}>
              Extracted high-impact obligations, discrepancies, conditions, and critical notes in {meta.name}.
            </p>
          </div>
          <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap", alignItems: "center" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
              <label style={{ fontSize: "0.8rem", color: "#64748b" }}>Priority:</label>
              <select
                className="workspace-select"
                value={priorityFilter}
                onChange={(e) => setPriorityFilter(e.target.value as any)}
                style={{ padding: "0.35rem 0.6rem", fontSize: "0.85rem" }}
              >
                <option value="all">All Priorities</option>
                <option value="high">High / Action Required</option>
                <option value="review">Review Needed</option>
                <option value="info">Informational</option>
              </select>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
              <label style={{ fontSize: "0.8rem", color: "#64748b" }}>Status:</label>
              <select
                className="workspace-select"
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value as any)}
                style={{ padding: "0.35rem 0.6rem", fontSize: "0.85rem" }}
              >
                <option value="all">All Statuses</option>
                <option value="pending">Pending Review</option>
                <option value="reviewed">Reviewed</option>
              </select>
            </div>
            <button
              className="workspace-btn workspace-btn-outline"
              onClick={fetchFindings}
              style={{ padding: "0.35rem 0.75rem", fontSize: "0.85rem", display: "inline-flex", alignItems: "center", gap: "0.35rem" }}
            >
              <RefreshCw size={14} /> Refresh
            </button>
          </div>
        </div>
      </div>

      {error && (
        <div style={{ padding: "1rem", background: "#fef2f2", border: "1px solid #fecaca", borderRadius: "8px", color: "#b91c1c", marginBottom: "1rem" }}>
          {error}
        </div>
      )}

      {loading ? (
        <div style={{ textAlign: "center", padding: "3rem", color: "#64748b" }}>
          Loading findings...
        </div>
      ) : findings.length === 0 ? (
        <div className="workspace-empty-state">
          <div style={{ fontSize: "2.5rem", marginBottom: "0.5rem" }}>🔍</div>
          <h3>No findings match the current filter</h3>
          <p style={{ color: "#64748b" }}>
            Upload documents to this workspace or change your filter settings.
          </p>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          {findings.map((f) => {
            const isHigh = f.review_priority === "high";
            const isReview = f.review_priority === "review";
            return (
              <div
                key={f.id}
                className="workspace-finding-card"
                style={{
                  borderLeft: `4px solid ${isHigh ? "#ef4444" : isReview ? "#f59e0b" : "#3b82f6"}`,
                  opacity: f.is_reviewed ? 0.75 : 1,
                  background: f.is_reviewed ? "#f8fafc" : "#ffffff",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "1rem", marginBottom: "0.5rem" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", flexWrap: "wrap" }}>
                    <span className={`workspace-finding-badge priority-${f.review_priority}`}>
                      {f.review_priority === "high" && <AlertCircle size={12} style={{ display: "inline", marginRight: "3px" }} />}
                      {f.review_priority === "review" && <AlertTriangle size={12} style={{ display: "inline", marginRight: "3px" }} />}
                      {f.review_priority === "info" && <Info size={12} style={{ display: "inline", marginRight: "3px" }} />}
                      {f.review_priority.toUpperCase()}
                    </span>
                    <span style={{ fontSize: "0.75rem", color: "#64748b", textTransform: "uppercase", fontWeight: 600 }}>
                      {f.finding_type}
                    </span>
                    {f.is_reviewed && (
                      <span style={{ fontSize: "0.75rem", color: "#059669", background: "#ecfdf5", padding: "2px 8px", borderRadius: "4px", fontWeight: 600, display: "inline-flex", alignItems: "center", gap: "3px" }}>
                        <CheckCircle size={12} /> Reviewed
                      </span>
                    )}
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                    {onSelectDoc && (
                      <button
                        className="workspace-btn workspace-btn-outline"
                        style={{ padding: "0.25rem 0.6rem", fontSize: "0.75rem" }}
                        onClick={() => onSelectDoc(f.document_id)}
                      >
                        View Source Document
                      </button>
                    )}
                    <button
                      className="workspace-btn workspace-btn-outline"
                      style={{ padding: "0.25rem 0.6rem", fontSize: "0.75rem" }}
                      disabled={updatingId === f.id}
                      onClick={() => handleToggleReviewed(f)}
                    >
                      {f.is_reviewed ? "Mark Unreviewed" : "Mark Reviewed"}
                    </button>
                  </div>
                </div>

                <h4 style={{ margin: "0 0 0.5rem 0", color: "#0f172a", fontSize: "1rem" }}>
                  {f.title}
                </h4>

                <p style={{ margin: "0 0 0.75rem 0", color: "#334155", fontSize: "0.9rem", lineHeight: 1.5 }}>
                  {f.explanation}
                </p>

                {f.why_it_matters && (
                  <div style={{ marginBottom: "0.75rem", background: "#f1f5f9", padding: "0.6rem 0.8rem", borderRadius: "6px", fontSize: "0.85rem" }}>
                    <strong style={{ color: "#0f172a" }}>Why it matters: </strong>
                    <span style={{ color: "#475569" }}>{f.why_it_matters}</span>
                  </div>
                )}

                {f.source_excerpt && (
                  <div className="workspace-evidence-box">
                    <div className="workspace-evidence-label">
                      SOURCE EVIDENCE {f.source_page ? `(Page ${f.source_page})` : ""} {f.source_section ? `[${f.source_section}]` : ""}
                    </div>
                    &ldquo;{f.source_excerpt}&rdquo;
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
