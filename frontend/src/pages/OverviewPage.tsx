import React, { useEffect, useState } from 'react';
import { NavLink } from 'react-router-dom';
import {
  FileText,
  UploadCloud,
  Clock,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  TrendingUp,
  FolderOpen,
  Sparkles,
  Layers,
  ChevronRight,
} from 'lucide-react';
import api from '../services/api';
import type { DashboardStats } from '../types';
import StatusBadge from '../components/common/StatusBadge';
import { useAuth } from '../hooks/useAuth';

export const OverviewPage: React.FC = () => {
  const { user } = useAuth();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const data = await api.getDashboardStats();
        setStats(data);
      } catch (err) {
        console.error('Failed to load dashboard statistics:', err);
      } finally {
        setIsLoading(false);
      }
    };
    fetchStats();
  }, []);

  return (
    <div className="space-y-8">
      {/* ── Top Header & Greeting ─────────────────────────────────── */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-semibold px-2 py-0.5 rounded-md bg-[#F0EEFF] text-[#6257F5] border border-[#6257F5]/20">
              Medical Workspace
            </span>
            <span className="text-xs text-[#77758A]">Personal Health Records</span>
          </div>
          <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight text-[#292443]">
            Welcome back, {user?.fullName?.split(' ')[0] || 'User'} 👋
          </h1>
          <p className="mt-1 text-sm text-[#77758A]">
            Here is the current status of your analysed reports and tracked lab parameters.
          </p>
        </div>

        <NavLink
          to="/app/upload"
          className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl bg-[#6257F5] hover:bg-[#5148d4] text-white text-sm font-semibold shadow-md shadow-violet-500/25 transition shrink-0"
        >
          <UploadCloud className="w-4 h-4" />
          <span>Upload Medical Report</span>
        </NavLink>
      </div>

      {/* ── Summary Strip (Activity Counts - NEVER a Health Score) ──── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white p-5 rounded-2xl border border-[#E8E7F0] shadow-sm">
          <div className="flex items-center justify-between text-xs text-[#77758A] font-medium">
            <span>Total Reports</span>
            <FolderOpen className="w-4 h-4 text-[#6257F5]" />
          </div>
          <div className="mt-2 text-2xl font-black text-[#292443]">
            {isLoading ? '...' : stats?.reportCount ?? 0}
          </div>
          <p className="text-[11px] text-[#77758A] mt-1">Uploaded to your archive</p>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-[#E8E7F0] shadow-sm">
          <div className="flex items-center justify-between text-xs text-[#77758A] font-medium">
            <span>Analysed Reports</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="mt-2 text-2xl font-black text-[#292443]">
            {isLoading ? '...' : stats?.analysedCount ?? 0}
          </div>
          <p className="text-[11px] text-[#77758A] mt-1">Extracted & grounded</p>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-[#E8E7F0] shadow-sm">
          <div className="flex items-center justify-between text-xs text-[#77758A] font-medium">
            <span>Tracked Parameters</span>
            <TrendingUp className="w-4 h-4 text-[#22B8B0]" />
          </div>
          <div className="mt-2 text-2xl font-black text-[#292443]">
            {isLoading ? '...' : stats?.trackedParameterCount ?? 0}
          </div>
          <p className="text-[11px] text-[#77758A] mt-1">Standardized analytes</p>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-[#E8E7F0] shadow-sm">
          <div className="flex items-center justify-between text-xs text-[#77758A] font-medium">
            <span>Needs Review</span>
            <AlertTriangle className="w-4 h-4 text-amber-500" />
          </div>
          <div className="mt-2 text-2xl font-black text-[#292443]">
            {isLoading ? '...' : stats?.needsReviewCount ?? 0}
          </div>
          <p className="text-[11px] text-[#77758A] mt-1">Check source snippet</p>
        </div>
      </div>

      {/* ── Main Content Grid: Recent Reports & Insights ──────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Recent Records Table / List */}
        <div className="lg:col-span-2 bg-white rounded-2xl border border-[#E8E7F0] shadow-sm p-6 flex flex-col">
          <div className="flex items-center justify-between mb-5">
            <div>
              <h2 className="text-base font-bold text-[#292443]">Recent Medical Documents</h2>
              <p className="text-xs text-[#77758A]">Reports uploaded and analysed</p>
            </div>
            <NavLink
              to="/app/records"
              className="text-xs font-semibold text-[#6257F5] hover:text-[#5148d4] flex items-center gap-1"
            >
              <span>View all records</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </NavLink>
          </div>

          {isLoading ? (
            <div className="py-12 text-center text-xs text-[#77758A]">Loading records...</div>
          ) : !stats?.recentDocuments || stats.recentDocuments.length === 0 ? (
            <div className="py-12 text-center rounded-xl border border-dashed border-[#E8E7F0] bg-slate-50/50 my-auto">
              <FileText className="w-8 h-8 text-[#77758A] mx-auto mb-2 opacity-50" />
              <p className="text-sm font-semibold text-[#292443]">No medical records yet</p>
              <p className="text-xs text-[#77758A] mt-1 max-w-xs mx-auto">
                Upload your first laboratory report or prescription to start extracting structured insights.
              </p>
              <NavLink
                to="/app/upload"
                className="mt-4 inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-[#6257F5] text-white text-xs font-semibold"
              >
                <UploadCloud className="w-3.5 h-3.5" />
                <span>Upload Report</span>
              </NavLink>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-[#E8E7F0] text-[#77758A] font-semibold">
                    <th className="pb-3">Document</th>
                    <th className="pb-3">Type</th>
                    <th className="pb-3">Test Date</th>
                    <th className="pb-3">Status</th>
                    <th className="pb-3 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#E8E7F0]">
                  {stats.recentDocuments.map((doc) => (
                    <tr key={doc.id} className="hover:bg-slate-50 transition">
                      <td className="py-3.5 font-medium text-[#292443]">
                        <NavLink
                          to={`/app/records/${doc.id}`}
                          className="hover:text-[#6257F5] font-semibold flex items-center gap-2"
                        >
                          <FileText className="w-4 h-4 text-[#6257F5]" />
                          <span className="truncate max-w-[180px]">
                            {doc.documentTitle || doc.originalFilename}
                          </span>
                        </NavLink>
                      </td>
                      <td className="py-3.5 text-[#77758A]">
                        {doc.documentType.replace('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
                      </td>
                      <td className="py-3.5 text-[#77758A]">
                        {doc.testDate
                          ? new Date(doc.testDate).toLocaleDateString()
                          : 'Not stated'}
                      </td>
                      <td className="py-3.5">
                        <StatusBadge status={doc.processingStatus} size="sm" />
                      </td>
                      <td className="py-3.5 text-right">
                        <NavLink
                          to={`/app/records/${doc.id}`}
                          className="text-[#6257F5] font-semibold hover:underline"
                        >
                          Inspect
                        </NavLink>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Recent Insights & Observations */}
        <div className="bg-white rounded-2xl border border-[#E8E7F0] shadow-sm p-6 flex flex-col">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-base font-bold text-[#292443]">Report Findings</h2>
              <p className="text-xs text-[#77758A]">Flagged against printed ranges</p>
            </div>
            <NavLink
              to="/app/insights"
              className="text-xs font-semibold text-[#6257F5] hover:text-[#5148d4] flex items-center gap-1"
            >
              <span>View all</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </NavLink>
          </div>

          {isLoading ? (
            <div className="py-8 text-center text-xs text-[#77758A]">Loading findings...</div>
          ) : !stats?.recentFindings || stats.recentFindings.length === 0 ? (
            <div className="py-8 text-center text-xs text-[#77758A] my-auto">
              <Sparkles className="w-6 h-6 text-[#77758A] mx-auto mb-2 opacity-50" />
              <p>No abnormal flags or observations yet.</p>
            </div>
          ) : (
            <div className="space-y-3 overflow-y-auto max-h-[360px]">
              {stats.recentFindings.map((finding) => (
                <div
                  key={finding.id}
                  className="p-3.5 rounded-xl bg-[#F7F7FB] border border-[#E8E7F0] space-y-1.5"
                >
                  <div className="flex items-start justify-between gap-2">
                    <span className="font-semibold text-xs text-[#292443] leading-snug">
                      {finding.title}
                    </span>
                    <StatusBadge status={finding.findingType} size="sm" />
                  </div>
                  <p className="text-[11px] text-[#77758A] leading-relaxed line-clamp-2">
                    {finding.explanation}
                  </p>
                  {finding.evidence && finding.evidence.length > 0 && finding.evidence[0].snippet && (
                    <div className="text-[10px] text-[#6257F5] bg-white px-2 py-1 rounded border border-[#E8E7F0] truncate font-mono">
                      &quot;{finding.evidence[0].snippet}&quot;
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* ── Tracked Parameter Previews (Historical Strip) ─────────── */}
      {stats?.trackedParameterPreviews && stats.trackedParameterPreviews.length > 0 && (
        <div className="bg-white rounded-2xl border border-[#E8E7F0] shadow-sm p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-base font-bold text-[#292443]">Tracked Lab Parameters</h2>
              <p className="text-xs text-[#77758A]">Latest recorded values from your medical history</p>
            </div>
            <NavLink
              to="/app/analytics"
              className="text-xs font-semibold text-[#6257F5] hover:text-[#5148d4] flex items-center gap-1"
            >
              <span>Explore longitudinal trends</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </NavLink>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
            {stats.trackedParameterPreviews.map((param) => (
              <NavLink
                key={param.parameterCode}
                to={`/app/analytics?parameter=${param.parameterCode}`}
                className="p-4 rounded-xl border border-[#E8E7F0] bg-[#F7F7FB] hover:border-[#6257F5]/40 hover:bg-[#F0EEFF]/20 transition"
              >
                <div className="text-xs text-[#77758A] truncate font-medium">{param.category}</div>
                <div className="font-bold text-sm text-[#292443] truncate mt-0.5">
                  {param.displayName}
                </div>
                <div className="mt-2 text-xl font-black text-[#292443]">
                  {param.latestValue}{' '}
                  <span className="text-xs font-normal text-[#77758A]">{param.unit}</span>
                </div>
                <div className="mt-2 flex items-center justify-between">
                  <StatusBadge status={param.latestStatus} size="sm" />
                  <span className="text-[10px] text-[#77758A]">{param.readingCount} reading(s)</span>
                </div>
              </NavLink>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default OverviewPage;

