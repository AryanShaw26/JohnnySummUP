import React, { useEffect, useState } from 'react';
import { NavLink } from 'react-router-dom';
import {
  Sparkles,
  AlertTriangle,
  TrendingDown,
  TrendingUp,
  HelpCircle,
  ExternalLink,
  ShieldCheck,
  FileText,
} from 'lucide-react';
import api from '../services/api';
import type { MedicalFinding } from '../types';
import StatusBadge from '../components/common/StatusBadge';

export const InsightsPage: React.FC = () => {
  const [findings, setFindings] = useState<MedicalFinding[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchInsights = async () => {
      try {
        const data = await api.getInsights();
        setFindings(data);
      } catch (err) {
        console.error('Failed to load insights:', err);
      } finally {
        setIsLoading(false);
      }
    };
    fetchInsights();
  }, []);

  const outOfRange = findings.filter(
    (f) => f.findingType === 'below_report_range' || f.findingType === 'above_report_range'
  );
  const labFlagged = findings.filter((f) => f.findingType === 'source_flagged');
  const needsReview = findings.filter((f) => f.findingType === 'needs_review');

  return (
    <div className="space-y-8">
      {/* ── Page Header ───────────────────────────────────────────── */}
      <div>
        <h1 className="text-2xl font-extrabold tracking-tight text-[#292443]">
          AI Medical Insights & Observations
        </h1>
        <p className="mt-1 text-xs text-[#77758A]">
          Evidence-linked findings transparently flagged against the reference intervals printed on your source reports.
        </p>
      </div>

      {isLoading ? (
        <div className="py-20 text-center text-xs text-[#77758A]">Loading insights...</div>
      ) : findings.length === 0 ? (
        <div className="bg-white p-12 rounded-2xl border border-[#E8E7F0] text-center space-y-3">
          <Sparkles className="w-10 h-10 text-[#6257F5]/40 mx-auto" />
          <h3 className="font-bold text-sm text-[#292443]">No observations flagged yet</h3>
          <p className="text-xs text-[#77758A] max-w-sm mx-auto">
            Once you upload lab reports, values falling outside printed reference intervals will be displayed here with their source evidence.
          </p>
          <NavLink
            to="/app/upload"
            className="inline-block mt-2 px-4 py-2 rounded-xl bg-[#6257F5] text-white text-xs font-semibold"
          >
            Upload Report
          </NavLink>
        </div>
      ) : (
        <div className="space-y-8">
          {/* Group 1: Outside Stated Reference Interval */}
          {outOfRange.length > 0 && (
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-amber-500"></span>
                <h2 className="text-sm font-bold text-[#292443]">
                  Outside Stated Reference Interval ({outOfRange.length})
                </h2>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {outOfRange.map((f) => (
                  <div
                    key={f.id}
                    className="bg-white p-5 rounded-2xl border border-[#E8E7F0] shadow-sm space-y-3"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <h3 className="font-bold text-xs text-[#292443] leading-snug">{f.title}</h3>
                      <StatusBadge status={f.findingType} size="sm" />
                    </div>
                    <p className="text-xs text-[#77758A] leading-relaxed">{f.explanation}</p>

                    {f.evidence && f.evidence.length > 0 && f.evidence[0].snippet && (
                      <div className="text-[11px] font-mono text-[#6257F5] bg-[#F7F7FB] px-2.5 py-1.5 rounded-lg border border-[#E8E7F0] truncate">
                        Evidence: &quot;{f.evidence[0].snippet}&quot;
                      </div>
                    )}

                    <div className="pt-2 border-t border-[#E8E7F0] flex items-center justify-between text-xs">
                      <span className="text-[11px] text-[#77758A]">Rule: {f.ruleCode || 'RR_CHECK'}</span>
                      <NavLink
                        to={`/app/records/${f.documentId}`}
                        className="text-[#6257F5] font-semibold hover:underline flex items-center gap-1"
                      >
                        <span>Inspect in Document</span>
                        <ExternalLink className="w-3 h-3" />
                      </NavLink>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Group 2: Laboratory Printed Markers */}
          {labFlagged.length > 0 && (
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-[#6257F5]"></span>
                <h2 className="text-sm font-bold text-[#292443]">
                  Source Laboratory Markers ({labFlagged.length})
                </h2>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {labFlagged.map((f) => (
                  <div
                    key={f.id}
                    className="bg-white p-5 rounded-2xl border border-[#E8E7F0] shadow-sm space-y-3"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <h3 className="font-bold text-xs text-[#292443] leading-snug">{f.title}</h3>
                      <StatusBadge status={f.findingType} size="sm" />
                    </div>
                    <p className="text-xs text-[#77758A] leading-relaxed">{f.explanation}</p>
                    <div className="pt-2 border-t border-[#E8E7F0] flex items-center justify-between text-xs">
                      <span className="text-[11px] text-[#77758A]">Source Flag Verified</span>
                      <NavLink
                        to={`/app/records/${f.documentId}`}
                        className="text-[#6257F5] font-semibold hover:underline flex items-center gap-1"
                      >
                        <span>Open Record</span>
                        <ExternalLink className="w-3 h-3" />
                      </NavLink>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Group 3: Items Needing Verification */}
          {needsReview.length > 0 && (
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-slate-400"></span>
                <h2 className="text-sm font-bold text-[#292443]">
                  Extraction Verification Recommended ({needsReview.length})
                </h2>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {needsReview.map((f) => (
                  <div
                    key={f.id}
                    className="bg-white p-5 rounded-2xl border border-[#E8E7F0] shadow-sm space-y-3"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <h3 className="font-bold text-xs text-[#292443] leading-snug">{f.title}</h3>
                      <StatusBadge status="needs_review" size="sm" />
                    </div>
                    <p className="text-xs text-[#77758A] leading-relaxed">{f.explanation}</p>
                    <div className="pt-2 border-t border-[#E8E7F0] flex items-center justify-between text-xs">
                      <span className="text-[11px] text-[#77758A]">Review against original</span>
                      <NavLink
                        to={`/app/records/${f.documentId}`}
                        className="text-[#6257F5] font-semibold hover:underline flex items-center gap-1"
                      >
                        <span>Review</span>
                        <ExternalLink className="w-3 h-3" />
                      </NavLink>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default InsightsPage;

