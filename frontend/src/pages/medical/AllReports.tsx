import { useEffect, useState } from "react";
import {
  Download,
  Eye,
  FileText,
  Plus,
  Search,
  Trash2,
} from "lucide-react";
import { Link } from "react-router-dom";
import { EmptyState } from "../../components/medical/EmptyState";
import { MedicalDisclaimer } from "../../components/medical/MedicalDisclaimer";
import { ReportStatusBadge } from "../../components/medical/ReportStatusBadge";
import { medicalApi } from "../../services/medicalApi";
import type { MedicalDocument } from "../../types/medical";

interface Props {
  fixedType?: "prescription" | "laboratory_report";
  titleOverride?: string;
  subtitleOverride?: string;
}

export function AllReportsPage({ fixedType, titleOverride, subtitleOverride }: Props) {
  const [reports, setReports] = useState<MedicalDocument[]>([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState<string>(fixedType || "all");
  const [sort, setSort] = useState("newest");

  // Deletion modal state
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

  const fetchReports = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await medicalApi.listDocuments({
        document_type: fixedType || typeFilter,
        search: search.trim() || undefined,
        sort,
        page,
        page_size: 10,
      });
      setReports(res.items);
      setTotal(res.total);
      setTotalPages(res.total_pages);
    } catch (err: any) {
      setError(err?.message || "Failed to load reports");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReports();
  }, [fixedType, typeFilter, sort, page]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchReports();
  };

  const handleDownload = async (doc: MedicalDocument) => {
    try {
      await medicalApi.downloadDocument(doc.id, doc.original_filename);
    } catch {
      alert("Failed to download document file.");
    }
  };

  const confirmDelete = async () => {
    if (!deleteId) return;
    setDeleting(true);
    try {
      await medicalApi.deleteDocument(deleteId);
      setDeleteId(null);
      fetchReports();
    } catch (err: any) {
      alert(err?.message || "Failed to delete document");
    } finally {
      setDeleting(false);
    }
  };

  const title = titleOverride || (fixedType === "prescription" ? "Prescriptions" : fixedType === "laboratory_report" ? "Laboratory Reports" : "All Medical Reports");
  const subtitle = subtitleOverride || (fixedType === "prescription" ? "View all extracted medical prescriptions and dosage information." : fixedType === "laboratory_report" ? "View and track all laboratory test results and blood work." : "Manage and view all your uploaded medical documents.");

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      {/* Header with Title and Upload CTA */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 14 }}>
        <div>
          <h2 style={{ fontSize: 24, margin: "0 0 4px" }}>{title}</h2>
          <p style={{ color: "var(--muted)", fontSize: 13, margin: 0 }}>
            {subtitle}
          </p>
        </div>
        <Link to="/app/medical/documents/upload" className="button button--primary button--compact">
          <Plus size={16} aria-hidden="true" />
          <span>Upload Report</span>
        </Link>
      </div>

      {/* Filter and Search Bar */}
      <div className="panel-card" style={{ padding: "14px 18px" }}>
        <form
          onSubmit={handleSearchSubmit}
          style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 12 }}
        >
          {/* Search Box */}
          <div className="field__control" style={{ minWidth: 260, flex: 1, minHeight: 40 }}>
            <Search size={16} style={{ color: "#9ca3af" }} />
            <input
              type="text"
              placeholder="Search reports by filename..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              style={{ padding: "8px 0" }}
            />
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
            {/* Type selector (only if not fixed) */}
            {!fixedType && (
              <select
                value={typeFilter}
                onChange={(e) => {
                  setTypeFilter(e.target.value);
                  setPage(1);
                }}
                className="button button--quiet"
                style={{
                  border: "1px solid var(--border)",
                  borderRadius: 10,
                  padding: "9px 14px",
                  fontSize: 12,
                  background: "#fff",
                }}
              >
                <option value="all">All Types</option>
                <option value="laboratory_report">Laboratory Reports</option>
                <option value="prescription">Prescriptions</option>
                <option value="other">Other Reports</option>
              </select>
            )}

            {/* Sort selector */}
            <select
              value={sort}
              onChange={(e) => {
                setSort(e.target.value);
                setPage(1);
              }}
              className="button button--quiet"
              style={{
                border: "1px solid var(--border)",
                borderRadius: 10,
                padding: "9px 14px",
                fontSize: 12,
                background: "#fff",
              }}
            >
              <option value="newest">Date (Newest)</option>
              <option value="oldest">Date (Oldest)</option>
              <option value="name_asc">Name (A-Z)</option>
              <option value="name_desc">Name (Z-A)</option>
            </select>

            <button type="submit" className="button button--primary button--compact" style={{ padding: "8px 14px" }}>
              Filter
            </button>
          </div>
        </form>
      </div>

      {/* Reports Table or Loading/Empty */}
      {loading ? (
        <div style={{ display: "flex", justifyContent: "center", padding: "60px 0" }}>
          <div className="spinner" />
        </div>
      ) : error ? (
        <div className="panel-card" style={{ textAlign: "center", padding: 30 }}>
          <p className="form-alert" style={{ marginBottom: 14 }}>{error}</p>
          <button type="button" onClick={fetchReports} className="button button--primary button--compact">
            Retry
          </button>
        </div>
      ) : reports.length === 0 ? (
        <EmptyState
          icon={FileText}
          title="No documents found"
          description={
            search || typeFilter !== "all"
              ? "No reports match your current filter or search criteria."
              : "Upload your first medical report to begin extracting insights."
          }
          actionText="Upload Medical Report"
          actionLink="/app/medical/documents/upload"
        />
      ) : (
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Report Name</th>
                <th>Type</th>
                <th>Date</th>
                <th>Status</th>
                <th style={{ textAlign: "right" }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {reports.map((doc) => {
                const repDate = doc.report_date
                  ? new Date(doc.report_date).toLocaleDateString(undefined, {
                      month: "short",
                      day: "numeric",
                      year: "numeric",
                    })
                  : new Date(doc.created_at).toLocaleDateString(undefined, {
                      month: "short",
                      day: "numeric",
                      year: "numeric",
                    });

                return (
                  <tr key={doc.id}>
                    <td>
                      <Link
                        to={`/app/medical/documents/${doc.id}`}
                        style={{ fontWeight: 600, color: "var(--purple)", display: "inline-flex", alignItems: "center", gap: 8 }}
                      >
                        <FileText size={16} />
                        <span>{doc.original_filename}</span>
                      </Link>
                    </td>
                    <td>
                      <span className="badge badge--purple">
                        {doc.document_type.replace("_", " ").toUpperCase()}
                      </span>
                    </td>
                    <td style={{ color: "#777085" }}>{repDate}</td>
                    <td>
                      <ReportStatusBadge status={doc.status} />
                    </td>
                    <td style={{ textAlign: "right" }}>
                      <div className="table-actions">
                        <Link
                          to={`/app/medical/documents/${doc.id}`}
                          className="action-btn"
                          title="View Report and AI Summary"
                        >
                          <Eye size={15} />
                        </Link>
                        <button
                          type="button"
                          className="action-btn"
                          title="Download Original File"
                          onClick={() => handleDownload(doc)}
                        >
                          <Download size={15} />
                        </button>
                        <button
                          type="button"
                          className="action-btn action-btn--danger"
                          title="Delete Report"
                          onClick={() => setDeleteId(doc.id)}
                        >
                          <Trash2 size={15} />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination Controls */}
      {totalPages > 1 && (
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 4px" }}>
          <span style={{ fontSize: 12, color: "var(--muted)" }}>
            Showing page {page} of {totalPages} ({total} reports)
          </span>
          <div style={{ display: "flex", gap: 8 }}>
            <button
              type="button"
              className="button button--quiet"
              disabled={page <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              style={{ border: "1px solid var(--border)", borderRadius: 8, padding: "6px 12px", fontSize: 12 }}
            >
              Previous
            </button>
            <button
              type="button"
              className="button button--quiet"
              disabled={page >= totalPages}
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              style={{ border: "1px solid var(--border)", borderRadius: 8, padding: "6px 12px", fontSize: 12 }}
            >
              Next
            </button>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deleteId && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(32, 27, 49, 0.45)",
            backdropFilter: "blur(4px)",
            display: "grid",
            placeItems: "center",
            zIndex: 100,
            padding: 20,
          }}
        >
          <div className="panel-card" style={{ maxWidth: 440, width: "100%", padding: 28 }}>
            <h3 style={{ margin: "0 0 10px", fontSize: 18, color: "#991b1b" }}>Delete Document?</h3>
            <p style={{ fontSize: 13, color: "var(--muted)", margin: "0 0 20px", lineHeight: 1.6 }}>
              Are you sure you want to permanently delete this medical document? All extracted analyses, measurements, and flags for this report will be deleted.
            </p>
            <div style={{ display: "flex", justifyContent: "flex-end", gap: 10 }}>
              <button
                type="button"
                className="button button--quiet"
                onClick={() => setDeleteId(null)}
                disabled={deleting}
              >
                Cancel
              </button>
              <button
                type="button"
                className="button button--outline-danger"
                onClick={confirmDelete}
                disabled={deleting}
              >
                {deleting ? "Deleting..." : "Yes, Delete Document"}
              </button>
            </div>
          </div>
        </div>
      )}

      <MedicalDisclaimer />
    </div>
  );
}
