import React, { useEffect, useState } from 'react';
import { NavLink } from 'react-router-dom';
import {
  FileText,
  Search,
  Filter,
  Trash2,
  ExternalLink,
  UploadCloud,
  ChevronLeft,
  ChevronRight,
  GitCompare,
  Download,
} from 'lucide-react';
import api from '../services/api';
import type { MedicalDocumentItem } from '../types';
import StatusBadge from '../components/common/StatusBadge';

export const RecordsPage: React.FC = () => {
  const [records, setRecords] = useState<MedicalDocumentItem[]>([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [docTypeFilter, setDocTypeFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [isLoading, setIsLoading] = useState(true);

  const fetchRecords = async () => {
    setIsLoading(true);
    try {
      const res = await api.getDocuments({
        page,
        pageSize: 10,
        search: search || undefined,
        document_type: docTypeFilter || undefined,
        status: statusFilter || undefined,
      });
      setRecords(res.items);
      setTotal(res.total);
      setTotalPages(res.totalPages);
    } catch (err) {
      console.error('Failed to load documents:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchRecords();
  }, [page, docTypeFilter, statusFilter]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchRecords();
  };

  const handleDelete = async (id: string, name: string) => {
    if (window.confirm(`Are you sure you want to permanently delete "${name}"?`)) {
      try {
        await api.deleteDocument(id);
        fetchRecords();
      } catch (err) {
        alert('Failed to delete document.');
      }
    }
  };

  return (
    <div className="space-y-6">
      {/* ── Header ────────────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold tracking-tight text-[#292443]">
            My Medical Records
          </h1>
          <p className="mt-1 text-xs text-[#77758A]">
            Search, filter, and review all uploaded medical documents and lab reports.
          </p>
        </div>

        <NavLink
          to="/app/upload"
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-[#6257F5] hover:bg-[#5148d4] text-white text-xs font-semibold shadow-sm transition self-start"
        >
          <UploadCloud className="w-3.5 h-3.5" />
          <span>Upload New</span>
        </NavLink>
      </div>

      {/* ── Search & Filters Bar ──────────────────────────────────── */}
      <div className="bg-white p-4 rounded-2xl border border-[#E8E7F0] shadow-sm flex flex-col md:flex-row items-center gap-3">
        <form onSubmit={handleSearchSubmit} className="relative flex-1 w-full">
          <Search className="w-4 h-4 text-[#77758A] absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by file name or report title..."
            className="w-full pl-9 pr-4 py-2 rounded-xl border border-[#E8E7F0] text-xs focus:border-[#6257F5] bg-[#F7F7FB]"
          />
        </form>

        <div className="flex items-center gap-2 w-full md:w-auto">
          <select
            value={docTypeFilter}
            onChange={(e) => {
              setDocTypeFilter(e.target.value);
              setPage(1);
            }}
            className="px-3 py-2 rounded-xl border border-[#E8E7F0] text-xs bg-white text-[#292443] font-medium"
          >
            <option value="">All Document Types</option>
            <option value="lab_report">Lab Report</option>
            <option value="prescription">Prescription</option>
            <option value="imaging_report">Imaging</option>
            <option value="discharge_summary">Discharge Summary</option>
          </select>

          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setPage(1);
            }}
            className="px-3 py-2 rounded-xl border border-[#E8E7F0] text-xs bg-white text-[#292443] font-medium"
          >
            <option value="">All Statuses</option>
            <option value="completed">Analysed</option>
            <option value="needs_review">Needs Review</option>
            <option value="processing">Processing</option>
            <option value="failed">Failed</option>
          </select>
        </div>
      </div>

      {/* ── Records Table ─────────────────────────────────────────── */}
      <div className="bg-white rounded-2xl border border-[#E8E7F0] shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="py-16 text-center text-xs text-[#77758A]">Loading records...</div>
        ) : records.length === 0 ? (
          <div className="py-16 text-center text-xs text-[#77758A]">
            <FileText className="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p className="font-semibold text-sm text-[#292443]">No records found</p>
            <p className="mt-1">Try adjusting your filters or upload a new medical document.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="bg-[#F7F7FB] border-b border-[#E8E7F0] text-[#77758A] font-semibold">
                  <th className="py-3 px-5">Document</th>
                  <th className="py-3 px-4">Type</th>
                  <th className="py-3 px-4">Test Date</th>
                  <th className="py-3 px-4">Uploaded</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-center">Data Extracted</th>
                  <th className="py-3 px-5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E8E7F0]">
                {records.map((doc) => (
                  <tr key={doc.id} className="hover:bg-slate-50 transition">
                    <td className="py-3.5 px-5 font-semibold text-[#292443]">
                      <NavLink
                        to={`/app/records/${doc.id}`}
                        className="hover:text-[#6257F5] flex items-center gap-2"
                      >
                        <FileText className="w-4 h-4 text-[#6257F5] shrink-0" />
                        <span className="truncate max-w-[220px]">
                          {doc.documentTitle || doc.originalFilename}
                        </span>
                      </NavLink>
                    </td>

                    <td className="py-3.5 px-4 text-[#77758A]">
                      {doc.documentType.replace('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
                    </td>

                    <td className="py-3.5 px-4 text-[#292443]">
                      {doc.testDate
                        ? new Date(doc.testDate).toLocaleDateString()
                        : <span className="text-[#77758A] italic">Not stated</span>}
                    </td>

                    <td className="py-3.5 px-4 text-[#77758A]">
                      {new Date(doc.uploadedAt).toLocaleDateString()}
                    </td>

                    <td className="py-3.5 px-4">
                      <StatusBadge status={doc.processingStatus} size="sm" />
                    </td>

                    <td className="py-3.5 px-4 text-center text-[#77758A]">
                      <span className="font-semibold text-[#292443]">{doc.measurementCount}</span> results
                      {doc.findingCount > 0 && (
                        <span className="ml-1.5 text-amber-600 font-semibold">
                          ({doc.findingCount} flagged)
                        </span>
                      )}
                    </td>

                    <td className="py-3.5 px-5 text-right space-x-2">
                      <NavLink
                        to={`/app/records/${doc.id}`}
                        className="inline-flex items-center gap-1 text-[#6257F5] font-semibold hover:underline"
                      >
                        <span>Open</span>
                        <ExternalLink className="w-3 h-3" />
                      </NavLink>

                      <button
                        onClick={() => handleDelete(doc.id, doc.documentTitle || doc.originalFilename)}
                        title="Delete Record"
                        className="text-[#77758A] hover:text-[#C93636] p-1 transition"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* ── Pagination ────────────────────────────────────────────── */}
        {totalPages > 1 && (
          <div className="p-4 border-t border-[#E8E7F0] flex items-center justify-between text-xs text-[#77758A]">
            <span>
              Showing {records.length} of {total} records
            </span>
            <div className="flex items-center gap-2">
              <button
                disabled={page <= 1}
                onClick={() => setPage(page - 1)}
                className="p-1.5 rounded-lg border border-[#E8E7F0] hover:bg-slate-50 disabled:opacity-40"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span className="font-semibold text-[#292443]">
                Page {page} of {totalPages}
              </span>
              <button
                disabled={page >= totalPages}
                onClick={() => setPage(page + 1)}
                className="p-1.5 rounded-lg border border-[#E8E7F0] hover:bg-slate-50 disabled:opacity-40"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default RecordsPage;

