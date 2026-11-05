import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  GitCompare,
  FileText,
  Calendar,
  AlertCircle,
  CheckCircle2,
  ChevronRight,
} from 'lucide-react';
import api from '../services/api';
import type { ComparisonData, MedicalDocumentItem } from '../types';
import StatusBadge from '../components/common/StatusBadge';

export const ComparePage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const preselectedDocId = searchParams.get('doc');

  const [availableDocs, setAvailableDocs] = useState<MedicalDocumentItem[]>([]);
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>(
    preselectedDocId ? [preselectedDocId] : []
  );
  const [comparison, setComparison] = useState<ComparisonData | null>(null);
  const [isLoadingDocs, setIsLoadingDocs] = useState(true);
  const [isComparing, setIsComparing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchDocs = async () => {
      try {
        const res = await api.getDocuments({ pageSize: 50 });
        setAvailableDocs(res.items);
        if (preselectedDocId && res.items.length >= 2 && selectedDocIds.length === 1) {
          const second = res.items.find((d) => d.id !== preselectedDocId);
          if (second) {
            setSelectedDocIds([preselectedDocId, second.id]);
          }
        }
      } catch (err) {
        console.error('Failed to load documents:', err);
      } finally {
        setIsLoadingDocs(false);
      }
    };
    fetchDocs();
  }, [preselectedDocId]);

  const handleToggleDoc = (docId: string) => {
    if (selectedDocIds.includes(docId)) {
      setSelectedDocIds(selectedDocIds.filter((id) => id !== docId));
    } else {
      if (selectedDocIds.length >= 3) {
        alert('You can compare up to 3 reports simultaneously.');
        return;
      }
      setSelectedDocIds([...selectedDocIds, docId]);
    }
  };

  const handleRunComparison = async () => {
    if (selectedDocIds.length < 2) {
      setError('Please select at least 2 reports to compare.');
      return;
    }
    setError(null);
    setIsComparing(true);
    try {
      const data = await api.compareReports(selectedDocIds);
      setComparison(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Comparison failed.');
    } finally {
      setIsComparing(false);
    }
  };

  useEffect(() => {
    if (selectedDocIds.length >= 2) {
      handleRunComparison();
    }
  }, [selectedDocIds.length]);

  return (
    <div className="space-y-6">
      {/* ── Page Header ───────────────────────────────────────────── */}
      <div>
        <h1 className="text-2xl font-extrabold tracking-tight text-[#292443]">
          Compare Medical Reports
        </h1>
        <p className="mt-1 text-xs text-[#77758A]">
          Align test results across multiple dates to inspect changes side by side.
        </p>
      </div>

      {error && (
        <div className="p-3.5 rounded-xl bg-red-50 border border-red-200 text-xs text-[#C93636] flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* ── Document Selector Strip ───────────────────────────────── */}
      <div className="bg-white p-5 rounded-2xl border border-[#E8E7F0] shadow-sm space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold text-[#292443]">
            Select Reports to Compare (Selected: {selectedDocIds.length}/3)
          </span>
          <button
            onClick={handleRunComparison}
            disabled={selectedDocIds.length < 2 || isComparing}
            className="px-4 py-1.5 rounded-xl bg-[#6257F5] hover:bg-[#5148d4] text-white text-xs font-semibold shadow-sm transition disabled:opacity-40"
          >
            {isComparing ? 'Comparing...' : 'Compare Selected'}
          </button>
        </div>

        {isLoadingDocs ? (
          <div className="py-6 text-center text-xs text-[#77758A]">Loading records...</div>
        ) : availableDocs.length === 0 ? (
          <div className="text-xs text-[#77758A]">No reports found in your account.</div>
        ) : (
          <div className="flex flex-wrap gap-2.5">
            {availableDocs.map((doc) => {
              const isSelected = selectedDocIds.includes(doc.id);
              return (
                <button
                  key={doc.id}
                  onClick={() => handleToggleDoc(doc.id)}
                  className={`px-3.5 py-2 rounded-xl text-xs font-medium border text-left transition flex items-center gap-2 ${
                    isSelected
                      ? 'border-[#6257F5] bg-[#F0EEFF] text-[#6257F5] font-semibold'
                      : 'border-[#E8E7F0] bg-[#F7F7FB] text-[#77758A] hover:border-slate-300'
                  }`}
                >
                  <FileText className="w-3.5 h-3.5 shrink-0" />
                  <div className="truncate max-w-[140px]">
                    <span className="block truncate">{doc.documentTitle || doc.originalFilename}</span>
                    <span className="text-[10px] text-slate-500 block">
                      {doc.testDate ? new Date(doc.testDate).toLocaleDateString() : 'Date N/A'}
                    </span>
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* ── Comparison Results Table ──────────────────────────────── */}
      {comparison && comparison.documents.length >= 2 && (
        <div className="bg-white rounded-2xl border border-[#E8E7F0] shadow-sm overflow-hidden">
          <div className="p-5 border-b border-[#E8E7F0]">
            <h3 className="font-bold text-sm text-[#292443]">Aligned Parameter Comparison</h3>
            <p className="text-xs text-[#77758A]">
              Comparing {comparison.documents.length} reports across {comparison.alignedMeasurements.length} parameters
            </p>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="bg-[#F7F7FB] border-b border-[#E8E7F0]">
                  <th className="py-3 px-5 text-[#77758A] font-semibold">Test Parameter</th>
                  {comparison.documents.map((d) => (
                    <th key={d.id} className="py-3 px-4 font-bold text-[#292443]">
                      <div className="truncate max-w-[180px]">{d.title}</div>
                      <div className="text-[10px] font-normal text-[#77758A]">
                        {d.testDate || 'Date not stated'}
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E8E7F0]">
                {comparison.alignedMeasurements.map((m, idx) => (
                  <tr key={idx} className="hover:bg-slate-50">
                    <td className="py-3 px-5 font-semibold text-[#292443]">
                      <div>{m.parameterName}</div>
                      {m.unit && <div className="text-[10px] font-normal text-[#77758A]">{m.unit}</div>}
                    </td>

                    {comparison.documents.map((d) => {
                      const reading = m.valuesByDocument[d.id];
                      return (
                        <td key={d.id} className="py-3 px-4">
                          {reading ? (
                            <div className="space-y-1">
                              <div className="font-bold text-[#292443] text-sm">
                                {reading.rawValue}{' '}
                                {m.unit && <span className="text-xs font-normal text-[#77758A]">{m.unit}</span>}
                              </div>
                              <div className="text-[10px] text-[#77758A]">
                                Ref: {reading.referenceText || 'Not stated'}
                              </div>
                              <StatusBadge status={reading.status} size="sm" />
                            </div>
                          ) : (
                            <span className="text-slate-400 italic text-[11px]">— Not tested —</span>
                          )}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default ComparePage;

