import { useEffect, useState } from "react";
import { BrainCircuit, Eye, Sparkles } from "lucide-react";
import { Link } from "react-router-dom";
import { EmptyState } from "../../components/medical/EmptyState";
import { MedicalDisclaimer } from "../../components/medical/MedicalDisclaimer";
import { medicalApi } from "../../services/medicalApi";
import type { DocumentAnalysis, MedicalDocument } from "../../types/medical";

export function PreviousSummariesPage() {
  const [summaries, setSummaries] = useState<DocumentAnalysis[]>([]);
  const [docMap, setDocMap] = useState<Record<string, MedicalDocument>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchSummaries = async () => {
      setLoading(true);
      setError(null);
      try {
        const [sumRes, docRes] = await Promise.all([
          medicalApi.getSummaryHistory(),
          medicalApi.listDocuments({ page_size: 50 }),
        ]);
        setSummaries(sumRes);
        const map: Record<string, MedicalDocument> = {};
        for (const d of docRes.items) {
          map[d.id] = d;
        }
        setDocMap(map);
      } catch (err: any) {
        setError(err?.message || "Failed to load summary history");
      } finally {
        setLoading(false);
      }
    };
    fetchSummaries();
  }, []);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div>
        <p className="eyebrow" style={{ color: "var(--purple)", marginBottom: 6 }}>
          HISTORY
        </p>
        <h2 style={{ fontSize: 24, margin: "0 0 4px" }}>Previous Summaries</h2>
        <p style={{ color: "var(--muted)", fontSize: 13, margin: 0 }}>
          Browse all previously generated plain-language AI summaries for your health reports.
        </p>
      </div>

      {loading ? (
        <div style={{ display: "flex", justifyContent: "center", padding: "60px 0" }}>
          <div className="spinner" />
        </div>
      ) : error ? (
        <div className="panel-card" style={{ textAlign: "center", padding: 30 }}>
          <p className="form-alert" style={{ marginBottom: 14 }}>{error}</p>
          <button type="button" onClick={() => window.location.reload()} className="button button--primary button--compact">
            Retry
          </button>
        </div>
      ) : summaries.length === 0 ? (
        <EmptyState
          icon={BrainCircuit}
          title="No generated summaries found"
          description="Upload and analyze reports to view saved AI summaries."
          actionText="Upload Medical Report"
          actionLink="/app/medical/documents/upload"
        />
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {summaries.map((analysis) => {
            const doc = docMap[analysis.document_id];
            const dateStr = new Date(analysis.created_at).toLocaleDateString(undefined, {
              month: "short",
              day: "numeric",
              year: "numeric",
            });

            return (
              <div
                key={analysis.id}
                className="panel-card"
                style={{ display: "flex", flexDirection: "column", gap: 12, padding: "20px 24px" }}
              >
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 10 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <div
                      style={{
                        width: 36,
                        height: 36,
                        borderRadius: 10,
                        background: "#f3ebfc",
                        color: "var(--purple)",
                        display: "grid",
                        placeItems: "center",
                      }}
                    >
                      <Sparkles size={18} />
                    </div>
                    <div>
                      <strong style={{ fontSize: 15, color: "var(--ink)" }}>
                        {doc ? doc.original_filename : "Medical Report"}
                      </strong>
                      <div style={{ fontSize: 11, color: "var(--muted)", marginTop: 2 }}>
                        Generated on {dateStr} • Version {analysis.version}
                        {doc && (
                          <span style={{ marginLeft: 8 }} className="badge badge--purple">
                            {doc.document_type.replace("_", " ").toUpperCase()}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>

                  <Link
                    to={`/app/medical/documents/${analysis.document_id}`}
                    className="button button--primary button--compact"
                    style={{ fontSize: 12 }}
                  >
                    <Eye size={14} />
                    <span>Open Summary</span>
                  </Link>
                </div>

                <p style={{ margin: "4px 0 0", fontSize: 13, color: "#4b4162", lineHeight: 1.6 }}>
                  {analysis.summary || "No summary text available."}
                </p>
              </div>
            );
          })}
        </div>
      )}

      <MedicalDisclaimer />
    </div>
  );
}
