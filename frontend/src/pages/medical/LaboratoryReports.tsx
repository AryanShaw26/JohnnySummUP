import { useEffect, useState } from "react";
import { Eye, FlaskConical, Plus, Search } from "lucide-react";
import { Link } from "react-router-dom";
import { EmptyState } from "../../components/medical/EmptyState";
import { MedicalDisclaimer } from "../../components/medical/MedicalDisclaimer";
import { ReportStatusBadge } from "../../components/medical/ReportStatusBadge";
import { medicalApi } from "../../services/medicalApi";
import type { MedicalDocumentDetail, MedicalMeasurement } from "../../types/medical";

interface LabReportItem {
  docId: string;
  docName: string;
  reportDate: string;
  status: string;
  measurements: MedicalMeasurement[];
}

export function LaboratoryReportsPage() {
  const [labReports, setLabReports] = useState<LabReportItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [error, setError] = useState<string | null>(null);

  const fetchLabReports = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await medicalApi.listDocuments({
        document_type: "laboratory_report",
        page_size: 50,
      });

      const items: LabReportItem[] = [];
      for (const doc of res.items) {
        try {
          const detail: MedicalDocumentDetail = await medicalApi.getDocumentDetails(doc.id);
          items.push({
            docId: doc.id,
            docName: doc.original_filename,
            reportDate: doc.report_date || doc.created_at,
            status: doc.status,
            measurements: detail.measurements,
          });
        } catch {
          items.push({
            docId: doc.id,
            docName: doc.original_filename,
            reportDate: doc.report_date || doc.created_at,
            status: doc.status,
            measurements: [],
          });
        }
      }
      setLabReports(items);
    } catch (err: any) {
      setError(err?.message || "Failed to load laboratory reports.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLabReports();
  }, []);

  const filtered = labReports.filter((item) => {
    if (!search.trim()) return true;
    const q = search.toLowerCase();
    if (item.docName.toLowerCase().includes(q)) return true;
    return item.measurements.some((m) => m.parameter_name.toLowerCase().includes(q));
  });

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 14 }}>
        <div>
          <p className="eyebrow" style={{ color: "var(--purple)", marginBottom: 6 }}>
            DOCUMENTS
          </p>
          <h2 style={{ fontSize: 24, margin: "0 0 4px" }}>Laboratory Reports</h2>
          <p style={{ color: "var(--muted)", fontSize: 13, margin: 0 }}>
            Blood tests, pathology panels, and measured biological markers.
          </p>
        </div>
        <Link to="/app/medical/documents/upload" className="button button--primary button--compact">
          <Plus size={16} />
          <span>Upload Lab Report</span>
        </Link>
      </div>

      {/* Filter and Search Bar */}
      <div className="panel-card" style={{ padding: "14px 18px" }}>
        <div className="field__control" style={{ maxWidth: 360, minHeight: 40 }}>
          <Search size={16} style={{ color: "#9ca3af" }} />
          <input
            type="text"
            placeholder="Search by test or parameter..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{ padding: "8px 0" }}
          />
        </div>
      </div>

      {loading ? (
        <div style={{ display: "flex", justifyContent: "center", padding: "60px 0" }}>
          <div className="spinner" />
        </div>
      ) : error ? (
        <div className="panel-card" style={{ textAlign: "center", padding: 30 }}>
          <p className="form-alert" style={{ marginBottom: 14 }}>{error}</p>
          <button type="button" onClick={fetchLabReports} className="button button--primary button--compact">
            Retry
          </button>
        </div>
      ) : filtered.length === 0 ? (
        <EmptyState
          icon={FlaskConical}
          title="No laboratory reports found"
          description={
            search
              ? "No laboratory reports match your search query."
              : "Upload blood tests, urinalysis, or pathology reports to track your laboratory parameters."
          }
          actionText="Upload Lab Report"
          actionLink="/app/medical/documents/upload"
        />
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {filtered.map((item) => {
            const dateStr = new Date(item.reportDate).toLocaleDateString(undefined, {
              month: "short",
              day: "numeric",
              year: "numeric",
            });

            return (
              <div key={item.docId} className="panel-card" style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 10 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                    <div
                      style={{
                        width: 40,
                        height: 40,
                        borderRadius: 12,
                        background: "#f0e9fb",
                        color: "var(--purple)",
                        display: "grid",
                        placeItems: "center",
                      }}
                    >
                      <FlaskConical size={20} />
                    </div>
                    <div>
                      <Link
                        to={`/app/medical/documents/${item.docId}`}
                        style={{ fontSize: 16, fontWeight: 700, color: "var(--ink)" }}
                      >
                        {item.docName}
                      </Link>
                      <div style={{ fontSize: 12, color: "var(--muted)", marginTop: 2 }}>
                        Report Date: {dateStr} • {item.measurements.length} test parameter{item.measurements.length !== 1 ? "s" : ""}
                      </div>
                    </div>
                  </div>

                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <ReportStatusBadge status={item.status} />
                    <Link
                      to={`/app/medical/documents/${item.docId}`}
                      className="button button--quiet"
                      style={{ border: "1px solid var(--border)", borderRadius: 8, padding: "6px 12px", fontSize: 12 }}
                    >
                      <Eye size={14} />
                      <span>View</span>
                    </Link>
                  </div>
                </div>

                {item.measurements.length === 0 ? (
                  <p style={{ margin: "4px 0 0", fontSize: 12, color: "var(--muted)", fontStyle: "italic" }}>
                    No numeric test values extracted yet. View the report summary or retry analysis.
                  </p>
                ) : (
                  <div className="table-container" style={{ border: "1px solid #f0edf6", borderRadius: 10 }}>
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Parameter</th>
                          <th>Measured Value</th>
                          <th>Unit</th>
                          <th>Stated Reference Range</th>
                          <th>Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {item.measurements.map((m) => {
                          let statusLabel = "Normal";
                          let badgeClass = "badge--green";
                          if (m.reference_high && m.numeric_value > m.reference_high) {
                            statusLabel = "High";
                            badgeClass = "badge--red";
                          } else if (m.reference_low && m.numeric_value < m.reference_low) {
                            statusLabel = "Low";
                            badgeClass = "badge--amber";
                          } else if (!m.reference_low && !m.reference_high) {
                            statusLabel = "Recorded";
                            badgeClass = "badge--gray";
                          }

                          return (
                            <tr key={m.id}>
                              <td style={{ fontWeight: 600 }}>{m.parameter_name}</td>
                              <td style={{ fontWeight: 700, color: "var(--purple)" }}>{m.numeric_value}</td>
                              <td>{m.unit}</td>
                              <td style={{ color: "var(--muted)" }}>
                                {m.reference_text || "Not supplied in report"}
                              </td>
                              <td>
                                <span className={`badge ${badgeClass}`}>{statusLabel}</span>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      <MedicalDisclaimer />
    </div>
  );
}
