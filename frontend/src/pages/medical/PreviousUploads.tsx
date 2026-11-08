import { useEffect, useState } from "react";
import { Download, Eye, FileText, Trash2, Upload } from "lucide-react";
import { Link } from "react-router-dom";
import { EmptyState } from "../../components/medical/EmptyState";
import { MedicalDisclaimer } from "../../components/medical/MedicalDisclaimer";
import { ReportStatusBadge } from "../../components/medical/ReportStatusBadge";
import { medicalApi } from "../../services/medicalApi";
import type { MedicalDocument } from "../../types/medical";

export function PreviousUploadsPage() {
  const [uploads, setUploads] = useState<MedicalDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchUploads = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await medicalApi.getUploadHistory();
      setUploads(res);
    } catch (err: any) {
      setError(err?.message || "Failed to load upload history");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUploads();
  }, []);

  const handleDownload = async (doc: MedicalDocument) => {
    try {
      await medicalApi.downloadDocument(doc.id, doc.original_filename);
    } catch {
      alert("Failed to download document file.");
    }
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm("Permanently delete this uploaded document?")) return;
    try {
      await medicalApi.deleteDocument(id);
      fetchUploads();
    } catch (err: any) {
      alert(err?.message || "Failed to delete document.");
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div>
        <p className="eyebrow" style={{ color: "var(--purple)", marginBottom: 6 }}>
          HISTORY
        </p>
        <h2 style={{ fontSize: 24, margin: "0 0 4px" }}>Previous Uploads</h2>
        <p style={{ color: "var(--muted)", fontSize: 13, margin: 0 }}>
          A complete chronological history of all your uploaded medical documents.
        </p>
      </div>

      {loading ? (
        <div style={{ display: "flex", justifyContent: "center", padding: "60px 0" }}>
          <div className="spinner" />
        </div>
      ) : error ? (
        <div className="panel-card" style={{ textAlign: "center", padding: 30 }}>
          <p className="form-alert" style={{ marginBottom: 14 }}>{error}</p>
          <button type="button" onClick={fetchUploads} className="button button--primary button--compact">
            Retry
          </button>
        </div>
      ) : uploads.length === 0 ? (
        <EmptyState
          icon={Upload}
          title="No uploaded documents"
          description="You haven't uploaded any medical reports yet."
          actionText="Upload First Document"
          actionLink="/app/medical/documents/upload"
        />
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {uploads.map((doc) => {
            const uploadDate = new Date(doc.created_at).toLocaleDateString(undefined, {
              month: "short",
              day: "numeric",
              year: "numeric",
            });

            return (
              <div
                key={doc.id}
                className="panel-card"
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "16px 22px",
                  gap: 16,
                  flexWrap: "wrap",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
                  <div
                    style={{
                      width: 44,
                      height: 44,
                      borderRadius: 12,
                      background: "#f1ebfb",
                      color: "var(--purple)",
                      display: "grid",
                      placeItems: "center",
                    }}
                  >
                    <FileText size={22} />
                  </div>
                  <div>
                    <Link
                      to={`/app/medical/documents/${doc.id}`}
                      style={{ fontWeight: 700, fontSize: 15, color: "var(--ink)", display: "block" }}
                    >
                      {doc.original_filename}
                    </Link>
                    <div style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 12, color: "var(--muted)", marginTop: 2 }}>
                      <span className="badge badge--purple">
                        {doc.document_type.replace("_", " ").toUpperCase()}
                      </span>
                      <span>Uploaded on {uploadDate}</span>
                      <span>•</span>
                      <span>{(doc.file_size_bytes / (1024 * 1024)).toFixed(2)} MB</span>
                    </div>
                  </div>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                  <ReportStatusBadge status={doc.status} />
                  <div className="table-actions">
                    <Link to={`/app/medical/documents/${doc.id}`} className="action-btn" title="View Report">
                      <Eye size={15} />
                    </Link>
                    <button
                      type="button"
                      className="action-btn"
                      title="Download Original"
                      onClick={() => handleDownload(doc)}
                    >
                      <Download size={15} />
                    </button>
                    <button
                      type="button"
                      className="action-btn action-btn--danger"
                      title="Delete"
                      onClick={() => handleDelete(doc.id)}
                    >
                      <Trash2 size={15} />
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      <MedicalDisclaimer />
    </div>
  );
}
