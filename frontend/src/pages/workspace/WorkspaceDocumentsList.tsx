import {
  Download,
  Eye,
  FileText,
  Plus,
  RefreshCw,
  Search,
  Trash2,
} from "lucide-react";
import { useEffect, useState } from "react";
import { workspaceApi } from "../../services/workspaceApi";
import type { WorkspaceDocument } from "../../types/workspace";
import type { WorkspaceMeta } from "./WorkspaceConfig";

interface Props {
  meta: WorkspaceMeta;
  onSelectDoc: (id: string) => void;
  onUploadClick: () => void;
}

export function WorkspaceDocumentsList({ meta, onSelectDoc, onUploadClick }: Props) {
  const [docs, setDocs] = useState<WorkspaceDocument[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [subtype, setSubtype] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [sort, setSort] = useState("newest");
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const fetchDocs = async () => {
    setLoading(true);
    try {
      const res = await workspaceApi.listDocuments(meta.backendSlug, {
        search,
        subtype,
        status_filter: statusFilter,
        sort,
        page,
        limit: 10,
      });
      setDocs(res.items);
      setTotal(res.total);
      setTotalPages(res.total_pages);
    } catch {
      setDocs([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocs();
  }, [meta.backendSlug, search, subtype, statusFilter, sort, page]);

  const handleDelete = async (docId: string, filename: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!window.confirm(`Are you sure you want to delete '${filename}'? This cannot be undone.`)) {
      return;
    }
    setDeletingId(docId);
    try {
      await workspaceApi.deleteDocument(meta.backendSlug, docId);
      await fetchDocs();
    } catch (err: any) {
      alert(err?.message || "Failed to delete document.");
    } finally {
      setDeletingId(null);
    }
  };

  const handleDownload = (docId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    window.open(workspaceApi.getDownloadUrl(meta.backendSlug, docId), "_blank");
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {/* Search & Filter Toolbar */}
      <div
        className="card"
        style={{
          padding: "16px 20px",
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 12,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 10, flex: 1, minWidth: 260 }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              background: "#f7f6fc",
              border: "1px solid var(--border)",
              borderRadius: 10,
              padding: "8px 12px",
              width: "100%",
            }}
          >
            <Search size={16} style={{ color: "var(--muted)" }} />
            <input
              type="text"
              placeholder={`Search ${meta.name} documents by name or type...`}
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
              style={{
                border: "none",
                background: "transparent",
                outline: "none",
                width: "100%",
                fontSize: 13.5,
              }}
            />
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
          {/* Subtype Filter */}
          <select
            value={subtype}
            onChange={(e) => {
              setSubtype(e.target.value);
              setPage(1);
            }}
            style={{
              padding: "8px 12px",
              borderRadius: 8,
              border: "1px solid var(--border)",
              background: "#fff",
              fontSize: 13,
            }}
          >
            <option value="all">All Document Types</option>
            {meta.subtypes.map((st) => (
              <option key={st.value} value={st.value}>
                {st.label}
              </option>
            ))}
          </select>

          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setPage(1);
            }}
            style={{
              padding: "8px 12px",
              borderRadius: 8,
              border: "1px solid var(--border)",
              background: "#fff",
              fontSize: 13,
            }}
          >
            <option value="all">All Statuses</option>
            <option value="completed">Completed</option>
            <option value="analyzing">Analyzing</option>
            <option value="failed">Failed</option>
          </select>

          {/* Sort */}
          <select
            value={sort}
            onChange={(e) => setSort(e.target.value)}
            style={{
              padding: "8px 12px",
              borderRadius: 8,
              border: "1px solid var(--border)",
              background: "#fff",
              fontSize: 13,
            }}
          >
            <option value="newest">Newest First</option>
            <option value="oldest">Oldest First</option>
            <option value="filename">Filename (A-Z)</option>
          </select>

          <button className="button button--compact button--primary" onClick={onUploadClick}>
            <Plus size={15} /> Upload
          </button>
        </div>
      </div>

      {/* Table Card */}
      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        {loading ? (
          <div style={{ textAlign: "center", padding: 48 }}>
            <RefreshCw size={24} className="spin" style={{ color: "var(--purple)", margin: "0 auto 12px" }} />
            <p style={{ color: "var(--muted)", margin: 0 }}>Fetching {meta.name} documents...</p>
          </div>
        ) : docs.length === 0 ? (
          <div style={{ textAlign: "center", padding: "48px 16px" }}>
            <FileText size={36} style={{ color: "#cfc6ea", margin: "0 auto 12px" }} />
            <h4 style={{ margin: "0 0 6px", fontSize: 16, color: "var(--ink)" }}>No documents found</h4>
            <p style={{ color: "var(--muted)", margin: "0 0 16px", fontSize: 13.5 }}>
              {search || subtype !== "all" || statusFilter !== "all"
                ? "Try adjusting your filters or search terms."
                : `Get started by uploading your first ${meta.name} document.`}
            </p>
            <button className="button button--compact button--primary" onClick={onUploadClick}>
              Upload Document
            </button>
          </div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table className="workspace-table">
              <thead>
                <tr>
                  <th>Document</th>
                  <th>Type</th>
                  <th>Pages / Format</th>
                  <th>Upload Date</th>
                  <th>Status</th>
                  <th style={{ textAlign: "right" }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {docs.map((doc) => (
                  <tr
                    key={doc.id}
                    onClick={() => onSelectDoc(doc.id)}
                    style={{ cursor: "pointer" }}
                  >
                    <td>
                      <div>
                        <strong style={{ fontSize: 14, color: "var(--ink)" }}>
                          {doc.label || doc.original_filename}
                        </strong>
                        {doc.label && doc.label !== doc.original_filename && (
                          <div style={{ fontSize: 11, color: "var(--muted)" }}>
                            {doc.original_filename}
                          </div>
                        )}
                      </div>
                    </td>
                    <td>
                      <span className="pill pill--muted" style={{ textTransform: "capitalize" }}>
                        {doc.document_subtype || doc.document_type}
                      </span>
                    </td>
                    <td>
                      <span style={{ fontSize: 12, color: "#5d5475" }}>
                        {doc.page_count} pg • {doc.file_extension.toUpperCase().replace(".", "")}
                      </span>
                    </td>
                    <td>
                      <span style={{ fontSize: 12, color: "var(--muted)" }}>
                        {new Date(doc.created_at).toLocaleDateString()}
                      </span>
                    </td>
                    <td>
                      <span className={`badge-status badge-status--${doc.status}`}>
                        {doc.status}
                      </span>
                    </td>
                    <td>
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "flex-end",
                          gap: 6,
                        }}
                      >
                        <button
                          className="button button--compact button--quiet"
                          onClick={(e) => {
                            e.stopPropagation();
                            onSelectDoc(doc.id);
                          }}
                          title="View analysis details"
                        >
                          <Eye size={15} />
                        </button>
                        <button
                          className="button button--compact button--quiet"
                          onClick={(e) => handleDownload(doc.id, e)}
                          title="Download original document"
                        >
                          <Download size={15} />
                        </button>
                        <button
                          className="button button--compact button--quiet"
                          style={{ color: "var(--danger)" }}
                          disabled={deletingId === doc.id}
                          onClick={(e) => handleDelete(doc.id, doc.original_filename, e)}
                          title="Delete document"
                        >
                          <Trash2 size={15} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination Footer */}
        {totalPages > 1 && (
          <div
            style={{
              padding: "14px 20px",
              borderTop: "1px solid var(--border)",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              fontSize: 13,
              color: "var(--muted)",
            }}
          >
            <span>
              Showing {docs.length} of {total} documents
            </span>
            <div style={{ display: "flex", gap: 8 }}>
              <button
                className="button button--compact button--quiet"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                Previous
              </button>
              <span style={{ display: "inline-flex", alignItems: "center", padding: "0 8px" }}>
                Page {page} of {totalPages}
              </span>
              <button
                className="button button--compact button--quiet"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
