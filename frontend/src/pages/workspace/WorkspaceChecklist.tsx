import React, { useEffect, useState } from "react";
import { CheckCircle2, Clock, ListChecks, RefreshCw } from "lucide-react";
import type { WorkspaceFinding } from "../../types/workspace";
import { workspaceApi } from "../../services/workspaceApi";
import type { WorkspaceMeta } from "./WorkspaceConfig";

interface Props {
  meta: WorkspaceMeta;
  onSelectDoc?: (docId: string) => void;
}

interface ChecklistItem {
  id: string;
  documentId: string;
  title: string;
  details: string;
  type: "deadline" | "obligation" | "action";
  source?: string;
  priority: string;
  completed: boolean;
}

export const WorkspaceChecklist: React.FC<Props> = ({ meta, onSelectDoc }) => {
  const [items, setItems] = useState<ChecklistItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadChecklist = async () => {
    try {
      setLoading(true);
      setError(null);

      // Load documents in this workspace
      const docsRes = await workspaceApi.listDocuments(meta.backendSlug, { limit: 20 });
      const checklistItems: ChecklistItem[] = [];

      // For completed docs, inspect structured data
      for (const doc of docsRes.items) {
        if (doc.status === "completed") {
          try {
            const analysis = await workspaceApi.getAnalysis(meta.backendSlug, doc.id);
            const data = analysis.structured_data || {};

            // 1. Deadlines / dates
            const deadlines = data.deadlines || data.critical_dates || data.important_dates || [];
            if (Array.isArray(deadlines)) {
              deadlines.forEach((d: any, idx: number) => {
                const dateStr = typeof d === "string" ? d : d.date || d.deadline || "";
                const desc = typeof d === "string" ? d : d.description || d.title || d.event || "";
                checklistItems.push({
                  id: `${doc.id}-dl-${idx}`,
                  documentId: doc.id,
                  title: `Deadline: ${dateStr ? dateStr + " - " : ""}${desc}`,
                  details: `Source: ${doc.original_filename} (${doc.document_subtype || "document"})`,
                  type: "deadline",
                  source: d.source || d.page_or_section || undefined,
                  priority: "high",
                  completed: false,
                });
              });
            }

            // 2. Obligations / Key Requirements
            const obligations = data.obligations || data.action_items || data.next_steps || data.eligibility_criteria || [];
            if (Array.isArray(obligations)) {
              obligations.forEach((o: any, idx: number) => {
                const desc = typeof o === "string" ? o : o.description || o.title || o.obligation || JSON.stringify(o);
                checklistItems.push({
                  id: `${doc.id}-ob-${idx}`,
                  documentId: doc.id,
                  title: desc,
                  details: `Requirement from ${doc.original_filename}`,
                  type: "obligation",
                  source: o.source || o.section || undefined,
                  priority: o.priority || "review",
                  completed: false,
                });
              });
            }
          } catch {
            // ignore individual doc analysis failure
          }
        }
      }

      // Also load high/review findings
      const findings = await workspaceApi.getWorkspaceFindings(meta.backendSlug, { limit: 50 });
      findings.forEach((f: WorkspaceFinding) => {
        if (f.review_priority === "high" || f.review_priority === "review") {
          checklistItems.push({
            id: `f-${f.id}`,
            documentId: f.document_id,
            title: f.title,
            details: f.explanation,
            type: "action",
            source: f.source_page ? `Page ${f.source_page}` : f.source_section || undefined,
            priority: f.review_priority,
            completed: f.is_reviewed,
          });
        }
      });

      setItems(checklistItems);
    } catch (err: any) {
      setError(err?.message || "Failed to load checklist");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadChecklist();
  }, [meta.backendSlug]);

  const toggleItem = (id: string) => {
    setItems((prev) =>
      prev.map((item) => (item.id === id ? { ...item, completed: !item.completed } : item))
    );
  };

  const completedCount = items.filter((i) => i.completed).length;
  const progressPercent = items.length > 0 ? Math.round((completedCount / items.length) * 100) : 0;

  return (
    <div className="workspace-checklist-view">
      <div className="workspace-card" style={{ marginBottom: "1.25rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "1rem" }}>
          <div>
            <h3 style={{ margin: 0, fontSize: "1.25rem", color: "#0f172a" }}>Action Items & Obligations Checklist</h3>
            <p style={{ margin: "0.25rem 0 0 0", color: "#64748b", fontSize: "0.875rem" }}>
              Actionable milestones, deadlines, and requirements synthesized across your {meta.name} documents.
            </p>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
            <div style={{ textAlign: "right" }}>
              <div style={{ fontSize: "0.875rem", fontWeight: 600, color: "#0f172a" }}>
                {completedCount} of {items.length} Completed
              </div>
              <div style={{ fontSize: "0.75rem", color: "#64748b" }}>
                {progressPercent}% resolution rate
              </div>
            </div>
            <div
              style={{
                width: "80px",
                height: "8px",
                background: "#e2e8f0",
                borderRadius: "4px",
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  width: `${progressPercent}%`,
                  height: "100%",
                  background: "#2563eb",
                  transition: "width 0.3s ease",
                }}
              />
            </div>
            <button
              className="workspace-btn workspace-btn-outline"
              onClick={loadChecklist}
              style={{ padding: "0.35rem 0.65rem", fontSize: "0.85rem", display: "inline-flex", alignItems: "center", gap: "0.35rem" }}
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
          Synthesizing action items from documents...
        </div>
      ) : items.length === 0 ? (
        <div className="workspace-empty-state">
          <ListChecks size={40} style={{ color: "#94a3b8", marginBottom: "0.5rem" }} />
          <h3>No action items or deadlines found</h3>
          <p style={{ color: "#64748b" }}>
            Upload documents to this workspace to extract deadlines, obligations, and required actions.
          </p>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
          {items.map((item) => (
            <div
              key={item.id}
              className="workspace-card"
              style={{
                display: "flex",
                alignItems: "flex-start",
                gap: "1rem",
                padding: "1rem",
                opacity: item.completed ? 0.6 : 1,
                background: item.completed ? "#f8fafc" : "#ffffff",
                borderLeft: `4px solid ${
                  item.type === "deadline"
                    ? "#ef4444"
                    : item.priority === "high"
                    ? "#f59e0b"
                    : "#3b82f6"
                }`,
              }}
            >
              <input
                type="checkbox"
                checked={item.completed}
                onChange={() => toggleItem(item.id)}
                style={{ marginTop: "0.3rem", width: "18px", height: "18px", cursor: "pointer" }}
              />

              <div style={{ flex: 1 }}>
                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", flexWrap: "wrap", marginBottom: "0.25rem" }}>
                  <span
                    style={{
                      fontSize: "0.7rem",
                      fontWeight: 700,
                      padding: "2px 6px",
                      borderRadius: "4px",
                      textTransform: "uppercase",
                      background: item.type === "deadline" ? "#fee2e2" : "#e0e7ff",
                      color: item.type === "deadline" ? "#b91c1c" : "#3730a3",
                      display: "inline-flex",
                      alignItems: "center",
                      gap: "3px",
                    }}
                  >
                    {item.type === "deadline" && <Clock size={10} />}
                    {item.type === "action" && <CheckCircle2 size={10} />}
                    {item.type}
                  </span>
                  {item.source && (
                    <span style={{ fontSize: "0.75rem", color: "#64748b" }}>
                      Ref: {item.source}
                    </span>
                  )}
                </div>

                <div
                  style={{
                    fontSize: "0.95rem",
                    fontWeight: 600,
                    color: item.completed ? "#64748b" : "#0f172a",
                    textDecoration: item.completed ? "line-through" : "none",
                    marginBottom: "0.25rem",
                  }}
                >
                  {item.title}
                </div>

                <div style={{ fontSize: "0.825rem", color: "#64748b" }}>
                  {item.details}
                </div>
              </div>

              {onSelectDoc && (
                <button
                  className="workspace-btn workspace-btn-outline"
                  style={{ padding: "0.25rem 0.5rem", fontSize: "0.75rem", whiteSpace: "nowrap" }}
                  onClick={() => onSelectDoc(item.documentId)}
                >
                  View Doc
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
