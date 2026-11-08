import { useEffect, useState } from "react";
import { BrainCircuit, FileText, Search } from "lucide-react";
import { Link } from "react-router-dom";
import { EmptyState } from "../../components/medical/EmptyState";
import { MedicalDisclaimer } from "../../components/medical/MedicalDisclaimer";
import { medicalApi } from "../../services/medicalApi";
import type { ExtractedFinding, MedicalDocument } from "../../types/medical";

export function ExtractedFindingsPage() {
  const [reports, setReports] = useState<MedicalDocument[]>([]);
  const [selectedDocId, setSelectedDocId] = useState<string>("all");
  const [findings, setFindings] = useState<Array<ExtractedFinding & { docName?: string; reportDate?: string }>>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  useEffect(() => {
    const loadAll = async () => {
      setLoading(true);
      try {
        const res = await medicalApi.listDocuments({ page_size: 50 });
        setReports(res.items);

        // Fetch details for all reports to gather findings
        const allFindings: Array<ExtractedFinding & { docName?: string; reportDate?: string }> = [];
        for (const doc of res.items) {
          try {
            const detail = await medicalApi.getDocumentDetails(doc.id);
            for (const f of detail.findings) {
              allFindings.push({
                ...f,
                docName: doc.original_filename,
                reportDate: doc.report_date || doc.created_at,
              });
            }
          } catch {
            // skip if failed
          }
        }
        setFindings(allFindings);
      } catch {
        // error handling
      } finally {
        setLoading(false);
      }
    };
    loadAll();
  }, []);

  const filtered = findings.filter((f) => {
    if (selectedDocId !== "all" && f.document_id !== selectedDocId) return false;
    if (search.trim()) {
      const q = search.toLowerCase();
      return (
        f.name.toLowerCase().includes(q) ||
        (f.docName && f.docName.toLowerCase().includes(q)) ||
        (f.value_text && f.value_text.toLowerCase().includes(q))
      );
    }
    return true;
  });

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div>
        <p className="eyebrow" style={{ color: "var(--purple)", marginBottom: 6 }}>
          AI ANALYSIS
        </p>
        <h2 style={{ fontSize: 24, margin: "0 0 4px" }}>Extracted Findings</h2>
        <p style={{ color: "var(--muted)", fontSize: 13, margin: 0 }}>
          Structured parameters and medical observations extracted from your uploaded documents.
        </p>
      </div>

      {/* Filter bar */}
      <div className="panel-card" style={{ padding: "14px 18px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
          <div className="field__control" style={{ minWidth: 260, flex: 1, minHeight: 40 }}>
            <Search size={16} style={{ color: "#9ca3af" }} />
            <input
              type="text"
              placeholder="Search findings by parameter or medicine..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              style={{ padding: "8px 0" }}
            />
          </div>

          <select
            value={selectedDocId}
            onChange={(e) => setSelectedDocId(e.target.value)}
            className="button button--quiet"
            style={{
              border: "1px solid var(--border)",
              borderRadius: 10,
              padding: "9px 14px",
              fontSize: 12,
              background: "#fff",
            }}
          >
            <option value="all">All Documents ({reports.length})</option>
            {reports.map((r) => (
              <option key={r.id} value={r.id}>
                {r.original_filename}
              </option>
            ))}
          </select>
        </div>
      </div>

      {loading ? (
        <div style={{ display: "flex", justifyContent: "center", padding: "60px 0" }}>
          <div className="spinner" />
        </div>
      ) : filtered.length === 0 ? (
        <EmptyState
          icon={BrainCircuit}
          title="No extracted findings found"
          description={
            findings.length === 0
              ? "Upload a medical report or prescription to automatically extract structured findings."
              : "No findings match your filter or search criteria."
          }
          actionText={findings.length === 0 ? "Upload Report" : undefined}
          actionLink={findings.length === 0 ? "/app/medical/documents/upload" : undefined}
        />
      ) : (
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Finding / Medicine</th>
                <th>Category</th>
                <th>Extracted Value</th>
                <th>Reference Range</th>
                <th>Source Document</th>
                <th>Page</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((f) => (
                <tr key={f.id}>
                  <td style={{ fontWeight: 600 }}>{f.name}</td>
                  <td>
                    <span className="badge badge--purple">{f.category}</span>
                  </td>
                  <td>
                    {f.value_text || (f.numeric_value !== null ? `${f.numeric_value} ${f.unit || ""}` : "—")}
                  </td>
                  <td style={{ color: "var(--muted)" }}>{f.reference_text || "Not supplied"}</td>
                  <td>
                    <Link
                      to={`/app/medical/documents/${f.document_id}`}
                      style={{ color: "var(--purple)", fontWeight: 600, display: "inline-flex", alignItems: "center", gap: 5 }}
                    >
                      <FileText size={14} />
                      <span>{f.docName || "View Report"}</span>
                    </Link>
                  </td>
                  <td style={{ color: "var(--muted)", fontSize: 12 }}>{f.source_page ?? 1}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <MedicalDisclaimer />
    </div>
  );
}
