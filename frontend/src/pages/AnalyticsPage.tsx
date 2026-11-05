import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  LineChart as LineChartIcon,
  TrendingUp,
  AlertCircle,
  CheckCircle2,
  Table as TableIcon,
  HelpCircle,
  Calendar,
} from 'lucide-react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceArea,
  Dot,
} from 'recharts';
import api from '../services/api';
import type { TrendData, TrendPoint } from '../types';
import StatusBadge from '../components/common/StatusBadge';

export const AnalyticsPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialParam = searchParams.get('parameter') || 'hemoglobin';

  const [parameters, setParameters] = useState<Array<{ parameterCode: string; displayName: string; category: string }>>([]);
  const [selectedParam, setSelectedParam] = useState(initialParam);
  const [trendData, setTrendData] = useState<TrendData | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Fetch parameter list
  useEffect(() => {
    const fetchParams = async () => {
      try {
        const list = await api.getParameters();
        setParameters(list);
      } catch (err) {
        console.error('Failed to load parameters:', err);
      }
    };
    fetchParams();
  }, []);

  // Fetch trend points for selected parameter
  useEffect(() => {
    const fetchTrend = async () => {
      setIsLoading(true);
      try {
        const data = await api.getTrends(selectedParam);
        setTrendData(data);
      } catch (err) {
        console.error('Failed to load trend data:', err);
      } finally {
        setIsLoading(false);
      }
    };
    fetchTrend();
  }, [selectedParam]);

  const handleParamChange = (code: string) => {
    setSelectedParam(code);
    setSearchParams({ parameter: code });
  };

  const chartData = trendData?.points.map((p) => ({
    date: p.testDate,
    value: p.value,
    unit: p.unit,
    refLow: p.referenceLow,
    refHigh: p.referenceHigh,
    status: p.calculatedRangeStatus,
    documentTitle: p.documentTitle,
  })) || [];

  return (
    <div className="space-y-6">
      {/* ── Page Header ───────────────────────────────────────────── */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold tracking-tight text-[#292443]">
            Health Analytics & Longitudinal Trends
          </h1>
          <p className="mt-1 text-xs text-[#77758A]">
            Track standardized laboratory measurements over time from verified report history.
          </p>
        </div>

        {/* Parameter Selector */}
        <div className="flex items-center gap-2">
          <label className="text-xs font-semibold text-[#77758A]">Parameter:</label>
          <select
            value={selectedParam}
            onChange={(e) => handleParamChange(e.target.value)}
            className="px-3.5 py-2 rounded-xl border border-[#E8E7F0] text-xs bg-white text-[#292443] font-semibold focus:border-[#6257F5]"
          >
            {parameters.map((p) => (
              <option key={p.parameterCode} value={p.parameterCode}>
                {p.displayName} ({p.category})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* ── Comparability Status Banner ────────────────────────────── */}
      {trendData && (
        <div
          className={`p-4 rounded-xl border text-xs flex items-center justify-between ${
            trendData.comparabilityStatus === 'comparable'
              ? 'bg-[#e8f5ee] border-emerald-200 text-[#168A4A]'
              : trendData.comparabilityStatus === 'incompatible_units'
              ? 'bg-amber-50 border-amber-200 text-amber-800'
              : 'bg-slate-50 border-slate-200 text-[#77758A]'
          }`}
        >
          <div className="flex items-center gap-2">
            {trendData.comparabilityStatus === 'comparable' ? (
              <CheckCircle2 className="w-4 h-4 shrink-0" />
            ) : (
              <AlertCircle className="w-4 h-4 shrink-0" />
            )}
            <div>
              <span className="font-bold">
                {trendData.comparabilityStatus === 'comparable'
                  ? 'Genuinely Comparable Historical Series'
                  : 'Comparability Notice'}
                :
              </span>{' '}
              {trendData.explanation}
            </div>
          </div>
          <span className="text-[11px] font-semibold bg-white/80 px-2 py-0.5 rounded border border-current">
            {trendData.points.length} Point(s)
          </span>
        </div>
      )}

      {/* ── Trend Chart Surface ───────────────────────────────────── */}
      <div className="bg-white p-6 rounded-2xl border border-[#E8E7F0] shadow-sm space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-[#E8E7F0]">
          <div>
            <h2 className="text-base font-bold text-[#292443]">
              {trendData?.displayName || 'Parameter'} Trend
            </h2>
            <p className="text-xs text-[#77758A]">
              Measured in <span className="font-semibold text-[#292443]">{trendData?.unit || 'standard units'}</span>
            </p>
          </div>
        </div>

        {isLoading ? (
          <div className="py-24 text-center text-xs text-[#77758A]">Loading trend data...</div>
        ) : chartData.length === 0 ? (
          <div className="py-24 text-center text-xs text-[#77758A]">
            <LineChartIcon className="w-8 h-8 mx-auto mb-2 opacity-40 text-[#6257F5]" />
            <p className="font-semibold text-sm text-[#292443]">No readings recorded yet</p>
            <p className="mt-1">Upload a medical report containing {selectedParam} to start tracking trends.</p>
          </div>
        ) : (
          <div className="h-72 w-full pt-4">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E8E7F0" />
                <XAxis
                  dataKey="date"
                  tick={{ fill: '#77758A', fontSize: 11 }}
                  tickLine={{ stroke: '#E8E7F0' }}
                />
                <YAxis
                  tick={{ fill: '#77758A', fontSize: 11 }}
                  tickLine={{ stroke: '#E8E7F0' }}
                  domain={['dataMin - 1', 'dataMax + 1']}
                />
                <Tooltip
                  content={({ active, payload }) => {
                    if (active && payload && payload.length) {
                      const data = payload[0].payload;
                      return (
                        <div className="bg-white p-3 rounded-xl border border-[#E8E7F0] shadow-md text-xs space-y-1">
                          <p className="font-bold text-[#292443]">{data.documentTitle || 'Medical Document'}</p>
                          <p className="text-[#77758A]">Date: {data.date}</p>
                          <p className="font-bold text-[#6257F5]">
                            Result: {data.value} {data.unit}
                          </p>
                          {data.refLow && data.refHigh && (
                            <p className="text-[#77758A]">
                              Report Range: {data.refLow} - {data.refHigh} {data.unit}
                            </p>
                          )}
                        </div>
                      );
                    }
                    return null;
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="value"
                  stroke="#6257F5"
                  strokeWidth={2.5}
                  dot={{ r: 5, fill: '#6257F5', strokeWidth: 2, stroke: '#FFFFFF' }}
                  activeDot={{ r: 7, fill: '#22B8B0' }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}

        <div className="pt-3 border-t border-[#E8E7F0] text-[11px] text-[#77758A] flex items-center justify-between">
          <span>* Each point preserves the reference interval printed on that specific source document.</span>
          <span className="text-[#6257F5] font-medium">Descriptive only — not a diagnosis</span>
        </div>
      </div>

      {/* ── Accessible Data Table Alternative ─────────────────────── */}
      {chartData.length > 0 && (
        <div className="bg-white rounded-2xl border border-[#E8E7F0] shadow-sm overflow-hidden">
          <div className="p-4 border-b border-[#E8E7F0] flex items-center gap-2">
            <TableIcon className="w-4 h-4 text-[#6257F5]" />
            <h3 className="font-bold text-xs text-[#292443]">Tabular Historical Data</h3>
          </div>

          <table className="w-full text-left text-xs">
            <thead>
              <tr className="bg-[#F7F7FB] border-b border-[#E8E7F0] text-[#77758A] font-semibold">
                <th className="py-2.5 px-4">Test Date</th>
                <th className="py-2.5 px-4">Result Value</th>
                <th className="py-2.5 px-4">Report Reference Interval</th>
                <th className="py-2.5 px-4">Status</th>
                <th className="py-2.5 px-4">Source Report</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#E8E7F0]">
              {chartData.map((row, idx) => (
                <tr key={idx} className="hover:bg-slate-50">
                  <td className="py-3 px-4 font-medium text-[#292443]">{row.date}</td>
                  <td className="py-3 px-4 font-bold text-[#292443]">
                    {row.value} {row.unit}
                  </td>
                  <td className="py-3 px-4 text-[#77758A]">
                    {row.refLow && row.refHigh ? `${row.refLow} - ${row.refHigh} ${row.unit}` : 'Not stated'}
                  </td>
                  <td className="py-3 px-4">
                    <StatusBadge status={row.status} size="sm" />
                  </td>
                  <td className="py-3 px-4 text-[#77758A] truncate max-w-[200px]">
                    {row.documentTitle}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default AnalyticsPage;

