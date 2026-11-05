import React, { useEffect, useState } from 'react';
import { NavLink } from 'react-router-dom';
import {
  Pill,
  ShieldCheck,
  AlertCircle,
  FileText,
  ExternalLink,
  Clock,
  Sparkles,
} from 'lucide-react';
import api from '../services/api';
import type { PrescriptionItem } from '../types';
import StatusBadge from '../components/common/StatusBadge';

export const PrescriptionsPage: React.FC = () => {
  const [prescriptions, setPrescriptions] = useState<PrescriptionItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchPrescriptions = async () => {
      try {
        const data = await api.getPrescriptions();
        setPrescriptions(data);
      } catch (err) {
        console.error('Failed to load prescriptions:', err);
      } finally {
        setIsLoading(false);
      }
    };
    fetchPrescriptions();
  }, []);

  return (
    <div className="space-y-6">
      {/* ── Page Header ───────────────────────────────────────────── */}
      <div>
        <h1 className="text-2xl font-extrabold tracking-tight text-[#292443]">
          Prescription Intelligence Archive
        </h1>
        <p className="mt-1 text-xs text-[#77758A]">
          Documented medications extracted strictly as written on original physician prescriptions.
        </p>
      </div>

      {/* Safety Notice */}
      <div className="p-4 rounded-xl bg-amber-50/70 border border-amber-200 text-xs text-amber-900 flex items-start gap-2.5">
        <ShieldCheck className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
        <div>
          <span className="font-bold">Strict Medication Safety Boundary:</span> JohnnySummUP extracts medication text
          verbatim and never infers missing dosages, frequencies, or durations. Never start, stop, or adjust prescription
          medications without direct physician supervision.
        </div>
      </div>

      {/* ── Prescriptions Grid ────────────────────────────────────── */}
      {isLoading ? (
        <div className="py-20 text-center text-xs text-[#77758A]">Loading prescriptions...</div>
      ) : prescriptions.length === 0 ? (
        <div className="bg-white p-12 rounded-2xl border border-[#E8E7F0] text-center space-y-3">
          <Pill className="w-10 h-10 text-[#6257F5]/40 mx-auto" />
          <h3 className="font-bold text-sm text-[#292443]">No prescriptions recorded yet</h3>
          <p className="text-xs text-[#77758A] max-w-sm mx-auto">
            Upload a doctor&apos;s prescription or discharge summary in the Upload section to extract medication instructions.
          </p>
          <NavLink
            to="/app/upload"
            className="inline-block mt-2 px-4 py-2 rounded-xl bg-[#6257F5] text-white text-xs font-semibold"
          >
            Upload Prescription
          </NavLink>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {prescriptions.map((rx) => (
            <div
              key={rx.id}
              className="bg-white p-5 rounded-2xl border border-[#E8E7F0] shadow-sm space-y-3"
            >
              <div className="flex items-start justify-between gap-2">
                <div>
                  <h3 className="font-bold text-sm text-[#292443] flex items-center gap-1.5">
                    <Pill className="w-4 h-4 text-[#6257F5]" />
                    <span>{rx.medicineName}</span>
                  </h3>
                  {rx.strength && (
                    <span className="text-xs text-[#6257F5] font-semibold">
                      Strength: {rx.strength}
                    </span>
                  )}
                </div>
                <StatusBadge status={rx.reviewStatus} size="sm" />
              </div>

              {rx.instructions && (
                <div className="p-3 rounded-xl bg-[#F7F7FB] border border-[#E8E7F0] text-xs text-[#292443]">
                  <span className="text-[10px] uppercase font-bold text-[#77758A] block mb-0.5">
                    Instructions
                  </span>
                  {rx.instructions}
                </div>
              )}

              {rx.sourceSnippet && (
                <div className="text-[11px] font-mono text-[#6257F5] bg-[#F0EEFF]/40 px-2.5 py-1.5 rounded-lg border border-[#6257F5]/20 truncate">
                  Snippet: &quot;{rx.sourceSnippet}&quot;
                </div>
              )}

              <div className="pt-2 border-t border-[#E8E7F0] flex items-center justify-between text-xs text-[#77758A]">
                <span>Document: {rx.documentTitle || 'Prescription'}</span>
                <NavLink
                  to={`/app/records/${rx.documentId}`}
                  className="text-[#6257F5] font-semibold hover:underline flex items-center gap-1"
                >
                  <span>Open Document</span>
                  <ExternalLink className="w-3 h-3" />
                </NavLink>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default PrescriptionsPage;

