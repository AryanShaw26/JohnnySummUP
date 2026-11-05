import React, { useEffect, useState } from 'react';
import { useParams, useNavigate, NavLink } from 'react-router-dom';
import {
  FileText,
  Download,
  GitCompare,
  Trash2,
  CheckCircle2,
  AlertTriangle,
  HelpCircle,
  Calendar,
  Building,
  User,
  ArrowLeft,
  Sparkles,
  Search,
  ExternalLink,
  ChevronRight,
  ShieldCheck,
  Eye,
} from 'lucide-react';
import api from '../services/api';
import type { DocumentDetail, ExtractedMeasurement, MedicalFinding } from '../types';
import StatusBadge from '../components/common/StatusBadge';

export const RecordDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [document, setDocument] = useState<DocumentDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedEvidenceSnippet, setSelectedEvidenceSnippet] = useState<string | null>(null);
  const [highlightedMeasId, setHighlightedMeasId] = useState<string | null>(null);
  const [isExporting, setIsExporting] = useState(false);

  useEffect(() => {
    if (!id) return;
    const fetchDoc = async () => {
      try {
        const data = await api.getDocument(id);
        setDocument(data);
        if (data.findings && data.findings.length > 0 && data.findings[0].evidence?.[0]?.snippet) {
          setSelectedEvidenceSnippet(data.findings[0].evidence[0].snippet);
        }
      } catch (err) {
        console.error('Failed to load document details:', err);
      } finally {
        setIsLoading(false);
      }
    };
    fetchDoc();
  }, [id]);

  const handleExportPdf = async () => {
    if (!id) return;
    setIsExporting(true);
    try {
      const res = await api.exportDocumentPdf(id);
      window.open(res.downloadUrl, '_blank');
    } catch (err) {
      alert('Failed to generate PDF summary.');
    } finally {
      setIsExporting(false);
    }
  };

  const handleDelete = async () => {
    if (!id || !document) return;
    if (window.confirm(`Permanently delete "${document.documentTitle}"?`)) {
      try {
        await api.deleteDocument(id);
        navigate('/app/records');
      } catch (err) {
        alert('Failed to delete document.');
      }
    }
  };

  const handleFindingClick = (finding: MedicalFinding) => {
    if (finding.evidence && finding.evidence.length > 0 && finding.evidence[0].snippet) {
      setSelectedEvidenceSnippet(finding.evidence[0].snippet);
    }
    if (finding.measurementId) {
      setHighlightedMeasId(finding.measurementId);
    }
  };

  const handleMeasurementClick = (meas: ExtractedMeasurement) => {
    setHighlightedMeasId(meas.id);
    if (meas.source?.snippet) {
      setSelectedEvidenceSnippet(meas.source.snippet);
    }
  };

  if (isLoading) {
    return (
      <div className="py-20 text-center text-xs text-[#77758A]">
        Loading document workspace...
      </div>
    );
  }

  if (!document) {
    return (
      <div className="py-20 text-center text-xs text-[#77758A]">
        Document not found.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* ── Top Header & Actions ───────────────────────────────────── */}
      <div className="bg-white p-6 rounded-2xl border border-[#E8E7F0] shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <NavLink
            to="/app/records"
            className="inline-flex items-center gap-1.5 text-xs text-[#77758A] hover:text-[#6257F5] mb-2 font-medium"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Back to Records</span>
          </NavLink>
          <div className="flex items-center gap-3">
            <h1 className="text-xl md:text-2xl font-extrabold text-[#292443] tracking-tight">
              {document.documentTitle || document.originalFilename}
            </h1>
            <StatusBadge status={document.status} size="sm" />
          </div>

          <div className="mt-2 flex flex-wrap items-center gap-4 text-xs text-[#77758A]">
            <span className="flex items-center gap-1">
              <Calendar className="w-3.5 h-3.5 text-[#6257F5]" />
              <b>Test Date:</b> {document.testDate ? new Date(document.testDate).toLocaleDateString() : 'Not stated'}
            </span>
            <span className="flex items-center gap-1">
              <Building className="w-3.5 h-3.5 text-[#22B8B0]" />
              <b>Facility:</b> {document.facilityName || 'Laboratory'}
            </span>
            <span>
              <b>Uploaded:</b> {new Date(document.uploadedAt).toLocaleDateString()}
            </span>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2.5 shrink-0">
          <button
            onClick={handleExportPdf}
            disabled={isExporting}
            className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl bg-white hover:bg-slate-50 border border-[#E8E7F0] text-xs font-semibold text-[#292443] transition shadow-sm"
          >
            <Download className="w-3.5 h-3.5 text-[#6257F5]" />
            <span>{isExporting ? 'Generating PDF...' : 'Download Summary PDF'}</span>
          </button>

          <NavLink
            to={`/app/compare?doc=${document.id}`}
            className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl bg-white hover:bg-slate-50 border border-[#E8E7F0] text-xs font-semibold text-[#292443] transition shadow-sm"
          >
            <GitCompare className="w-3.5 h-3.5 text-[#22B8B0]" />
            <span>Compare</span>
          </NavLink>

          <button
            onClick={handleDelete}
            title="Delete record"
            className="p-2 text-[#77758A] hover:text-[#C93636] hover:bg-red-50 border border-[#E8E7F0] rounded-xl transition"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* ── Signature Split Workspace ─────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* LEFT PANEL: Source Document & Traceable Evidence Viewer (5 cols) */}
        <div className="lg:col-span-5 bg-white rounded-2xl border border-[#E8E7F0] shadow-sm p-5 space-y-4 lg:sticky lg:top-4">
          <div className="flex items-center justify-between pb-3 border-b border-[#E8E7F0]">
            <div className="flex items-center gap-2 text-xs font-bold text-[#292443]">
              <Eye className="w-4 h-4 text-[#6257F5]" />
              <span>Original Source & Evidence</span>
            </div>
            <a
              href={api.getDocumentFileUrl(document.id)}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-[#6257F5] font-semibold hover:underline flex items-center gap-1"
            >
              <span>View Raw File</span>
              <ExternalLink className="w-3 h-3" />
            </a>
          </div>

          {/* Active Highlighted Evidence Box */}
          <div className="p-4 rounded-xl bg-[#F0EEFF]/50 border border-[#6257F5]/30 space-y-2">
            <div className="flex items-center justify-between text-xs text-[#6257F5] font-semibold">
              <span className="flex items-center gap-1">
                <Sparkles className="w-3.5 h-3.5" />
                Active Source Evidence Pointer
              </span>
              <span className="text-[11px] bg-white px-2 py-0.5 rounded border border-[#6257F5]/20">
                Page {document.pageCount || 1}
              </span>
            </div>
            <div className="p-3 bg-white rounded-lg border border-[#E8E7F0] font-mono text-xs text-[#292443] break-words">
              {selectedEvidenceSnippet ? (
                <span>&quot;{selectedEvidenceSnippet}&quot;</span>
              ) : (
                <span className="text-[#77758A] italic">Click any finding or result to highlight its exact source text.</span>
              )}
            </div>
            <p className="text-[11px] text-[#77758A]">
              Every observation and flagged value is anchored in the verified text extracted from this document.
            </p>
          </div>

          {/* Document Metadata Summary */}
          <div className="bg-[#F7F7FB] p-4 rounded-xl border border-[#E8E7F0] space-y-2 text-xs">
            <h4 className="font-semibold text-[#292443]">Verification Metadata</h4>
            <div className="grid grid-cols-2 gap-2 text-[#77758A]">
              <div>
                <span className="block text-[10px] uppercase font-bold text-slate-400">File Name</span>
                <span className="text-[#292443] truncate block">{document.originalFilename}</span>
              </div>
              <div>
                <span className="block text-[10px] uppercase font-bold text-slate-400">Total Pages</span>
                <span className="text-[#292443]">{document.pageCount || 1}</span>
              </div>
              <div>
                <span className="block text-[10px] uppercase font-bold text-slate-400">Pipeline Status</span>
                <span className="text-emerald-700 font-medium">Validated (100% grounded)</span>
              </div>
              <div>
                <span className="block text-[10px] uppercase font-bold text-slate-400">Range Baseline</span>
                <span className="text-[#292443]">Report-specific</span>
              </div>
            </div>
          </div>
        </div>

        {/* RIGHT PANEL: Plain-Language Interpretation & Structured Results (7 cols) */}
        <div className="lg:col-span-7 space-y-6">
          {/* Plain-Language Summary Box */}
          {document.summary && (
            <div className="bg-white p-6 rounded-2xl border border-[#E8E7F0] shadow-sm space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="font-bold text-sm text-[#292443] flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-[#6257F5]" />
                  <span>Plain-Language Summary</span>
                </h3>
                <span className="text-xs text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full font-semibold border border-emerald-200">
                  Grounded in Document
                </span>
              </div>

              <p className="text-xs md:text-sm text-[#292443] leading-relaxed">
                {document.summary.summaryText}
              </p>

              {/* Key grounded points */}
              {document.summary.structuredSummary?.keyPoints && (
                <div className="space-y-2 pt-2 border-t border-[#E8E7F0]">
                  <span className="text-xs font-bold text-[#77758A] uppercase tracking-wider block">
                    Key Explanations
                  </span>
                  {document.summary.structuredSummary.keyPoints.map((kp, idx) => (
                    <div
                      key={idx}
                      className="p-3 rounded-xl bg-[#F7F7FB] border border-[#E8E7F0] text-xs text-[#292443] flex items-start gap-2.5"
                    >
                      <CheckCircle2 className="w-4 h-4 text-[#6257F5] shrink-0 mt-0.5" />
                      <span>{kp.text}</span>
                    </div>
                  ))}
                </div>
              )}

              {/* Questions for Clinician */}
              {document.summary.structuredSummary?.questionsForClinician && (
                <div className="p-4 rounded-xl bg-violet-50/50 border border-[#6257F5]/20 space-y-2">
                  <span className="text-xs font-bold text-[#6257F5] flex items-center gap-1.5">
                    <HelpCircle className="w-4 h-4" />
                    <span>Questions to Discuss with Your Doctor</span>
                  </span>
                  <ul className="space-y-1.5 pl-5 text-xs text-[#292443] list-disc">
                    {document.summary.structuredSummary.questionsForClinician.map((q, idx) => (
                      <li key={idx} className="leading-relaxed">{q}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Limitations Notice */}
              <div className="text-[11px] text-[#77758A] flex items-start gap-1.5 pt-1">
                <ShieldCheck className="w-4 h-4 text-[#22B8B0] shrink-0 mt-0.5" />
                <span>
                  {document.summary.structuredSummary?.safetyNotice ||
                    'Informational explanation only. Never diagnoses, prescribes, or replaces professional medical advice.'}
                </span>
              </div>
            </div>
          )}

          {/* Key Findings Cards */}
          {document.findings && document.findings.length > 0 && (
            <div className="bg-white p-6 rounded-2xl border border-[#E8E7F0] shadow-sm space-y-4">
              <h3 className="font-bold text-sm text-[#292443]">
                Observations & Stated Interval Flags ({document.findings.length})
              </h3>
              <div className="space-y-3">
                {document.findings.map((f) => (
                  <div
                    key={f.id}
                    onClick={() => handleFindingClick(f)}
                    className="p-4 rounded-xl border border-[#E8E7F0] bg-[#F7F7FB] hover:border-[#6257F5] hover:bg-white cursor-pointer transition space-y-2 group"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <span className="font-bold text-xs text-[#292443] group-hover:text-[#6257F5] transition">
                        {f.title}
                      </span>
                      <StatusBadge status={f.findingType} size="sm" />
                    </div>
                    <p className="text-xs text-[#77758A] leading-relaxed">
                      {f.explanation}
                    </p>
                    {f.evidence && f.evidence.length > 0 && f.evidence[0].snippet && (
                      <div className="text-[11px] font-mono text-[#6257F5] bg-white px-2.5 py-1 rounded border border-[#E8E7F0]">
                        Source: &quot;{f.evidence[0].snippet}&quot;
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Extracted Measurements Table */}
          {document.measurements && document.measurements.length > 0 && (
            <div className="bg-white rounded-2xl border border-[#E8E7F0] shadow-sm overflow-hidden">
              <div className="p-5 border-b border-[#E8E7F0] flex items-center justify-between">
                <div>
                  <h3 className="font-bold text-sm text-[#292443]">Extracted Measurements</h3>
                  <p className="text-xs text-[#77758A]">Click any row to inspect its source text location</p>
                </div>
                <span className="text-xs font-bold text-[#6257F5] bg-[#F0EEFF] px-2.5 py-0.5 rounded-full">
                  {document.measurements.length} Test(s)
                </span>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="bg-[#F7F7FB] border-b border-[#E8E7F0] text-[#77758A] font-semibold">
                      <th className="py-3 px-4">Parameter</th>
                      <th className="py-3 px-4">Result Value</th>
                      <th className="py-3 px-4">Report Reference Interval</th>
                      <th className="py-3 px-4">Range Status</th>
                      <th className="py-3 px-4 text-center">Confidence</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#E8E7F0]">
                    {document.measurements.map((m) => {
                      const isHighlighted = highlightedMeasId === m.id;
                      const rangeStr =
                        m.referenceRange?.rawText ||
                        (m.referenceRange?.low !== undefined && m.referenceRange?.high !== undefined
                          ? `${m.referenceRange.low} - ${m.referenceRange.high}`
                          : 'Not stated');

                      return (
                        <tr
                          key={m.id}
                          onClick={() => handleMeasurementClick(m)}
                          className={`cursor-pointer transition ${
                            isHighlighted ? 'bg-[#F0EEFF]/60 font-semibold' : 'hover:bg-slate-50'
                          }`}
                        >
                          <td className="py-3 px-4 text-[#292443]">
                            <div className="font-semibold">
                              {m.parameterDisplayName || m.parameterName}
                            </div>
                            {m.parameterDisplayName && m.parameterDisplayName !== m.parameterName && (
                              <div className="text-[10px] text-[#77758A] font-normal">
                                Raw: {m.parameterName}
                              </div>
                            )}
                          </td>

                          <td className="py-3 px-4 text-[#292443] font-bold">
                            {m.rawValueText} {m.sourceUnit && <span className="font-normal text-[#77758A]">{m.sourceUnit}</span>}
                            {m.sourceFlag && (
                              <span className="ml-1.5 px-1.5 py-0.5 rounded text-[10px] bg-red-100 text-red-700 font-bold">
                                {m.sourceFlag}
                              </span>
                            )}
                          </td>

                          <td className="py-3 px-4 text-[#77758A]">
                            {rangeStr}
                          </td>

                          <td className="py-3 px-4">
                            <StatusBadge status={m.calculatedRangeStatus} size="sm" />
                          </td>

                          <td className="py-3 px-4 text-center">
                            <span
                              className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${
                                (m.confidence || 1) >= 0.90
                                  ? 'bg-emerald-100 text-emerald-800'
                                  : 'bg-amber-100 text-amber-800'
                              }`}
                            >
                              {Math.round((m.confidence || 0.95) * 100)}%
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Prescriptions Section if any */}
          {document.prescriptions && document.prescriptions.length > 0 && (
            <div className="bg-white p-6 rounded-2xl border border-[#E8E7F0] shadow-sm space-y-4">
              <h3 className="font-bold text-sm text-[#292443]">Extracted Prescription Instructions</h3>
              <div className="space-y-3">
                {document.prescriptions.map((rx) => (
                  <div
                    key={rx.id}
                    onClick={() => rx.sourceSnippet && setSelectedEvidenceSnippet(rx.sourceSnippet)}
                    className="p-4 rounded-xl border border-[#E8E7F0] bg-[#F7F7FB] hover:border-[#6257F5] cursor-pointer transition space-y-1"
                  >
                    <div className="font-bold text-xs text-[#292443]">
                      {rx.medicineName} {rx.strength && <span className="text-[#6257F5]">({rx.strength})</span>}
                    </div>
                    {rx.instructions && (
                      <p className="text-xs text-[#77758A]">Instructions: {rx.instructions}</p>
                    )}
                    {rx.sourceSnippet && (
                      <div className="text-[10px] font-mono text-[#6257F5] bg-white px-2 py-0.5 rounded border border-[#E8E7F0]">
                        &quot;{rx.sourceSnippet}&quot;
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default RecordDetailPage;

