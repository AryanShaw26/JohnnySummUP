import React, { useEffect, useState } from "react";
import { GitCompare, RefreshCw } from "lucide-react";
import type { WorkspaceCompareResponse, WorkspaceDocument } from "../../types/workspace";
import { workspaceApi } from "../../services/workspaceApi";
import type { WorkspaceMeta } from "./WorkspaceConfig";

interface Props {
  meta: WorkspaceMeta;
  onSelectDoc?: (docId: string) => void;
}

export const WorkspaceCompare: React.FC<Props> = ({ meta }) => {
  const [documents, setDocuments] = useState<WorkspaceDocument[]>([]);
  const [baseDocId, setBaseDocId] = useState<string>("");
  const [compareDocId, setCompareDocId] = useState<string>("");
  const [comparing, setComparing] = useState(false);
  const [result, setResult] = useState<WorkspaceCompareResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchDocs = async () => {
    try {
      const res = await workspaceApi.listDocuments(meta.backendSlug, { status_filter: "completed", limit: 50 });
      setDocuments(res.items);
      if (res.items.length >= 2) {
        setBaseDocId(res.items[0].id);
        setCompareDocId(res.items[1].id);
      } else if (res.items.length === 1) {
        setBaseDocId(res.items[0].id);
      }
    } catch {
      setError("Failed to fetch documents for comparison");
    }
  };

  useEffect(() => {
    fetchDocs();
  }, [meta.backendSlug]);

  const handleCompare = async () => {
    if (!baseDocId || !compareDocId) {
      setError("Please select two distinct documents to compare.");
      return;
    }
    if (baseDocId === compareDocId) {
      setError("Base document and comparison document must be different.");
      return;
    }

    try {
      setComparing(true);
      setError(null);
      const res = await workspaceApi.compareDocuments(meta.backendSlug, baseDocId, compareDocId);
      setResult(res);
    } catch (err: any) {
      setError(err?.message || "Comparison failed");
    } finally {
      setComparing(false);
    }
  };

  return (
    <div className="workspace-compare-view">
      <div className="workspace-card" style={{ marginBottom: "1.25rem" }}>
        <h3 style={{ margin: "0 0 0.5rem 0", fontSize: "1.25rem", color: "#0f172a" }}>
          Document Version & Contract Comparison
        </h3>
        <p style={{ margin: "0 0 1.25rem 0", color: "#64748b", fontSize: "0.875rem" }}>
          Compare two versions of an agreement, statement, policy, or record in {meta.name}. See structured field modifications, clause alterations, additions, and deletions.
        </p>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "1rem", alignItems: "flex-end" }}>
          <div>
            <label style={{ display: "block", fontSize: "0.85rem", fontWeight: 600, color: "#334155", marginBottom: "0.4rem" }}>
              Base Document (Original / V1)
            </label>
            <select
              className="workspace-select"
              value={baseDocId}
              onChange={(e) => setBaseDocId(e.target.value)}
              style={{ width: "100%" }}
            >
              <option value="">Select base document...</option>
              {documents.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.original_filename} ({d.document_subtype || "doc"}) - {new Date(d.created_at).toLocaleDateString()}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label style={{ display: "block", fontSize: "0.85rem", fontWeight: 600, color: "#334155", marginBottom: "0.4rem" }}>
              Comparison Document (Revised / V2)
            </label>
            <select
              className="workspace-select"
              value={compareDocId}
              onChange={(e) => setCompareDocId(e.target.value)}
              style={{ width: "100%" }}
            >
              <option value="">Select revised document...</option>
              {documents.map((d) => (
                <option key={d.id} value={d.id} disabled={d.id === baseDocId}>
                  {d.original_filename} ({d.document_subtype || "doc"}) - {new Date(d.created_at).toLocaleDateString()}
                </option>
              ))}
            </select>
          </div>

          <div>
            <button
              className="workspace-btn workspace-btn-primary"
              style={{ width: "100%", height: "42px", display: "inline-flex", alignItems: "center", justifyContent: "center", gap: "0.5rem" }}
              onClick={handleCompare}
              disabled={comparing || !baseDocId || !compareDocId || baseDocId === compareDocId}
            >
              {comparing ? (
                <>
                  <RefreshCw size={16} className="spin" /> Comparing Documents...
                </>
              ) : (
                <>
                  <GitCompare size={16} /> Run Side-by-Side Comparison
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {error && (
        <div style={{ padding: "1rem", background: "#fef2f2", border: "1px solid #fecaca", borderRadius: "8px", color: "#b91c1c", marginBottom: "1rem" }}>
          {error}
        </div>
      )}

      {result && (
        <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
          {/* Summary Card */}
          <div className="workspace-card">
            <h4 style={{ margin: "0 0 0.5rem 0", color: "#0f172a" }}>Comparison Summary</h4>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "1rem", marginTop: "0.75rem" }}>
              <div style={{ padding: "0.75rem", background: "#f8fafc", borderRadius: "6px" }}>
                <span style={{ fontSize: "0.75rem", color: "#64748b" }}>Changed Structured Fields</span>
                <div style={{ fontSize: "1.25rem", fontWeight: 700, color: "#0f172a" }}>
                  {result.summary_comparison.changed_fields_count}
                </div>
              </div>
              <div style={{ padding: "0.75rem", background: "#f0fdf4", borderRadius: "6px" }}>
                <span style={{ fontSize: "0.75rem", color: "#166534" }}>Added Sentences / Clauses</span>
                <div style={{ fontSize: "1.25rem", fontWeight: 700, color: "#16a34a" }}>
                  +{result.summary_comparison.total_additions_count}
                </div>
              </div>
              <div style={{ padding: "0.75rem", background: "#fef2f2", borderRadius: "6px" }}>
                <span style={{ fontSize: "0.75rem", color: "#991b1b" }}>Removed Sentences / Clauses</span>
                <div style={{ fontSize: "1.25rem", fontWeight: 700, color: "#dc2626" }}>
                  -{result.summary_comparison.total_deletions_count}
                </div>
              </div>
            </div>
          </div>

          {/* Structured Field Changes */}
          {result.field_changes && result.field_changes.length > 0 && (
            <div className="workspace-card">
              <h4 style={{ margin: "0 0 0.75rem 0", color: "#0f172a" }}>
                Key Field & Clause Changes ({result.field_changes.length})
              </h4>
              <div style={{ overflowX: "auto" }}>
                <table className="workspace-table">
                  <thead>
                    <tr>
                      <th style={{ width: "25%" }}>Field / Clause</th>
                      <th style={{ width: "37%" }}>{result.document_a.filename}</th>
                      <th style={{ width: "38%" }}>{result.document_b.filename}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.field_changes.map((fc: { field: string; document_a_value: any; document_b_value: any }, idx: number) => (
                      <tr key={idx}>
                        <td style={{ fontWeight: 600, color: "#1e293b" }}>{fc.field}</td>
                        <td style={{ background: "#fef2f2", color: "#991b1b", fontSize: "0.85rem" }}>
                          {typeof fc.document_a_value === "object" ? JSON.stringify(fc.document_a_value) : String(fc.document_a_value ?? "N/A")}
                        </td>
                        <td style={{ background: "#f0fdf4", color: "#166534", fontSize: "0.85rem" }}>
                          {typeof fc.document_b_value === "object" ? JSON.stringify(fc.document_b_value) : String(fc.document_b_value ?? "N/A")}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Additions and Deletions */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "1.25rem" }}>
            {/* Added clauses */}
            <div className="workspace-card" style={{ borderTop: "4px solid #10b981" }}>
              <h4 style={{ margin: "0 0 0.75rem 0", color: "#065f46" }}>
                Added Content ({result.sample_additions?.length || 0})
              </h4>
              {result.sample_additions && result.sample_additions.length > 0 ? (
                <ul style={{ margin: 0, paddingLeft: "1.25rem", color: "#334155", fontSize: "0.875rem", lineHeight: 1.6 }}>
                  {result.sample_additions.map((item: string, idx: number) => (
                    <li key={idx} style={{ marginBottom: "0.4rem" }}>{item}</li>
                  ))}
                </ul>
              ) : (
                <div style={{ color: "#64748b", fontSize: "0.85rem", fontStyle: "italic" }}>
                  No major additions detected.
                </div>
              )}
            </div>

            {/* Removed clauses */}
            <div className="workspace-card" style={{ borderTop: "4px solid #ef4444" }}>
              <h4 style={{ margin: "0 0 0.75rem 0", color: "#991b1b" }}>
                Removed / Missing Content ({result.sample_deletions?.length || 0})
              </h4>
              {result.sample_deletions && result.sample_deletions.length > 0 ? (
                <ul style={{ margin: 0, paddingLeft: "1.25rem", color: "#334155", fontSize: "0.875rem", lineHeight: 1.6 }}>
                  {result.sample_deletions.map((item: string, idx: number) => (
                    <li key={idx} style={{ marginBottom: "0.4rem" }}>{item}</li>
                  ))}
                </ul>
              ) : (
                <div style={{ color: "#64748b", fontSize: "0.85rem", fontStyle: "italic" }}>
                  No major removals detected.
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
