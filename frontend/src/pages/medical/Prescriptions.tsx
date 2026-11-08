import { useEffect, useState } from "react";
import { Eye, Pill, Plus, Search } from "lucide-react";
import { Link } from "react-router-dom";
import { EmptyState } from "../../components/medical/EmptyState";
import { MedicalDisclaimer } from "../../components/medical/MedicalDisclaimer";
import { ReportStatusBadge } from "../../components/medical/ReportStatusBadge";
import { medicalApi } from "../../services/medicalApi";
import type { ExtractedFinding, MedicalDocumentDetail } from "../../types/medical";

interface PrescriptionItem {
  docId: string;
  docName: string;
  reportDate: string;
  status: string;
  medicines: ExtractedFinding[];
}

export function PrescriptionsPage() {
  const [prescriptions, setPrescriptions] = useState<PrescriptionItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [error, setError] = useState<string | null>(null);

  const fetchPrescriptions = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await medicalApi.listDocuments({
        document_type: "prescription",
        page_size: 50,
      });

      const items: PrescriptionItem[] = [];
      for (const doc of res.items) {
        try {
          const detail: MedicalDocumentDetail = await medicalApi.getDocumentDetails(doc.id);
          const meds = detail.findings.filter(
            (f) => f.category === "prescription" || f.finding_type === "medicine"
          );
          items.push({
            docId: doc.id,
            docName: doc.original_filename,
            reportDate: doc.report_date || doc.created_at,
            status: doc.status,
            medicines: meds,
          });
        } catch {
          items.push({
            docId: doc.id,
            docName: doc.original_filename,
            reportDate: doc.report_date || doc.created_at,
            status: doc.status,
            medicines: [],
          });
        }
      }
      setPrescriptions(items);
    } catch (err: any) {
      setError(err?.message || "Failed to load prescriptions.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPrescriptions();
  }, []);

  const filtered = prescriptions.filter((p) => {
    if (!search.trim()) return true;
    const q = search.toLowerCase();
    if (p.docName.toLowerCase().includes(q)) return true;
    return p.medicines.some((m) => m.name.toLowerCase().includes(q));
  });

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 14 }}>
        <div>
          <p className="eyebrow" style={{ color: "var(--purple)", marginBottom: 6 }}>
            DOCUMENTS
          </p>
          <h2 style={{ fontSize: 24, margin: "0 0 4px" }}>Prescriptions</h2>
          <p style={{ color: "var(--muted)", fontSize: 13, margin: 0 }}>
            Extracted medical prescriptions, medications, and dosage instructions.
          </p>
        </div>
        <Link to="/app/medical/documents/upload" className="button button--primary button--compact">
          <Plus size={16} />
          <span>Upload Prescription</span>
        </Link>
      </div>

      {/* Filter and Search Bar */}
      <div className="panel-card" style={{ padding: "14px 18px" }}>
        <div className="field__control" style={{ maxWidth: 360, minHeight: 40 }}>
          <Search size={16} style={{ color: "#9ca3af" }} />
          <input
            type="text"
            placeholder="Search by medicine or document..."
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
          <button type="button" onClick={fetchPrescriptions} className="button button--primary button--compact">
            Retry
          </button>
        </div>
      ) : filtered.length === 0 ? (
        <EmptyState
          icon={Pill}
          title="No prescriptions found"
          description={
            search
              ? "No prescriptions match your search keyword."
              : "Upload a doctor's prescription or medication document to view extracted details."
          }
          actionText="Upload Prescription"
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
                      <Pill size={20} />
                    </div>
                    <div>
                      <Link
                        to={`/app/medical/documents/${item.docId}`}
                        style={{ fontSize: 16, fontWeight: 700, color: "var(--ink)" }}
                      >
                        {item.docName}
                      </Link>
                      <div style={{ fontSize: 12, color: "var(--muted)", marginTop: 2 }}>
                        Date: {dateStr} • {item.medicines.length} medicine{item.medicines.length !== 1 ? "s" : ""} detected
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

                {item.medicines.length === 0 ? (
                  <p style={{ margin: "4px 0 0", fontSize: 12, color: "var(--muted)", fontStyle: "italic" }}>
                    No individual medicines could be extracted. View the original document or retry analysis.
                  </p>
                ) : (
                  <div className="table-container" style={{ border: "1px solid #f0edf6", borderRadius: 10 }}>
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Medicine Name</th>
                          <th>Dosage / Instructions</th>
                          <th>Confidence</th>
                        </tr>
                      </thead>
                      <tbody>
                        {item.medicines.map((med) => (
                          <tr key={med.id}>
                            <td style={{ fontWeight: 600 }}>{med.name}</td>
                            <td style={{ color: "#4b4162" }}>
                              {med.value_text || "Not found in document"}
                            </td>
                            <td style={{ color: "var(--muted)", fontSize: 12 }}>
                              {med.confidence !== null && med.confidence !== undefined
                                ? `${Math.round(med.confidence * 100)}%`
                                : "N/A"}
                            </td>
                          </tr>
                        ))}
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
