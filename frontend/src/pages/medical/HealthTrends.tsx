import { useEffect, useState } from "react";
import { ArrowDown, ArrowUp, Minus, TrendingUp } from "lucide-react";
import { EmptyState } from "../../components/medical/EmptyState";
import { MedicalDisclaimer } from "../../components/medical/MedicalDisclaimer";
import { TrendChart } from "../../components/medical/TrendChart";
import { medicalApi } from "../../services/medicalApi";
import type { TrendResponse } from "../../types/medical";

export function HealthTrendsPage() {
  const [data, setData] = useState<TrendResponse | null>(null);
  const [selectedParam, setSelectedParam] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchTrends = async (param?: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await medicalApi.getTrends(param);
      setData(res);
      if (!selectedParam && res.parameter_name) {
        setSelectedParam(res.parameter_name);
      }
    } catch (err: any) {
      setError(err?.message || "Failed to load health trends");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTrends(selectedParam || undefined);
  }, [selectedParam]);

  const handleParamChange = (param: string) => {
    setSelectedParam(param);
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div>
        <p className="eyebrow" style={{ color: "var(--purple)", marginBottom: 6 }}>
          HEALTH ANALYTICS
        </p>
        <h2 style={{ fontSize: 24, margin: "0 0 4px" }}>Health Trends</h2>
        <p style={{ color: "var(--muted)", fontSize: 13, margin: 0 }}>
          Track changes in your key health parameters over time across uploaded lab reports.
        </p>
      </div>

      {loading ? (
        <div style={{ display: "flex", justifyContent: "center", padding: "60px 0" }}>
          <div className="spinner" />
        </div>
      ) : error ? (
        <div className="panel-card" style={{ textAlign: "center", padding: 30 }}>
          <p className="form-alert" style={{ marginBottom: 14 }}>{error}</p>
          <button type="button" onClick={() => fetchTrends(selectedParam)} className="button button--primary button--compact">
            Retry
          </button>
        </div>
      ) : !data || data.points.length === 0 ? (
        <EmptyState
          icon={TrendingUp}
          title="No health trend data available"
          description="Upload laboratory reports to track your blood and test parameters over time."
          actionText="Upload Laboratory Report"
          actionLink="/app/medical/documents/upload"
        />
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          {/* Parameter selector header */}
          <div className="panel-card" style={{ padding: "14px 20px", display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 12 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <span style={{ fontSize: 13, fontWeight: 700, color: "var(--ink)" }}>Parameter:</span>
              <select
                value={selectedParam}
                onChange={(e) => handleParamChange(e.target.value)}
                className="button button--quiet"
                style={{
                  border: "1px solid var(--border)",
                  borderRadius: 8,
                  padding: "8px 14px",
                  fontSize: 13,
                  fontWeight: 600,
                  background: "#fff",
                }}
              >
                {data.available_parameters.map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
              </select>
            </div>

            {data.reference_range && (
              <span className="badge badge--purple">
                Stated Range: {data.reference_range}
              </span>
            )}
          </div>

          {/* Chart and Current Value Card */}
          <div className="overview-grid">
            {/* SVG Trend Chart */}
            <div className="chart-card">
              <div className="chart-header">
                <div>
                  <h3 style={{ margin: "0 0 4px", fontSize: 16 }}>{data.parameter_name} Trend</h3>
                  <span style={{ fontSize: 12, color: "var(--muted)" }}>
                    Unit: {data.unit} {data.reference_range ? `• Range: ${data.reference_range}` : ""}
                  </span>
                </div>
              </div>

              <TrendChart
                points={data.points}
                parameterName={data.parameter_name}
                unit={data.unit}
                referenceRange={data.reference_range}
              />
            </div>

            {/* Current Value & Change Card */}
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <div className="panel-card" style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                <span style={{ fontSize: 12, color: "var(--muted)", fontWeight: 700 }}>LATEST RECORDED VALUE</span>
                <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
                  <span style={{ fontFamily: "Manrope, sans-serif", fontSize: 32, fontWeight: 800, color: "var(--ink)" }}>
                    {data.current_value}
                  </span>
                  <span style={{ fontSize: 14, fontWeight: 600, color: "var(--muted)" }}>
                    {data.unit}
                  </span>
                </div>

                <div>
                  <span
                    className={`badge ${
                      data.status === "high"
                        ? "badge--red"
                        : data.status === "low"
                        ? "badge--amber"
                        : "badge--green"
                    }`}
                  >
                    {data.status.toUpperCase()}
                  </span>
                </div>

                {data.change !== null && data.change !== undefined && (
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 6,
                      fontSize: 13,
                      color: data.change > 0 ? "var(--purple)" : data.change < 0 ? "#2563eb" : "var(--muted)",
                      paddingTop: 10,
                      borderTop: "1px solid #f0edf6",
                    }}
                  >
                    {data.change > 0 ? <ArrowUp size={16} /> : data.change < 0 ? <ArrowDown size={16} /> : <Minus size={16} />}
                    <span>
                      {data.change > 0 ? `+${data.change}` : data.change} {data.unit} (from previous report)
                    </span>
                  </div>
                )}
              </div>

              {/* Data Points List */}
              <div className="panel-card" style={{ padding: "18px 20px" }}>
                <h4 style={{ margin: "0 0 12px", fontSize: 13, color: "var(--ink)" }}>Recorded Measurements</h4>
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {data.points.map((p, idx) => (
                    <div
                      key={idx}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        padding: "8px 0",
                        borderBottom: idx < data.points.length - 1 ? "1px solid #f2edf8" : "none",
                        fontSize: 12,
                      }}
                    >
                      <span style={{ color: "var(--muted)" }}>{p.date}</span>
                      <strong style={{ color: p.is_abnormal ? "#dc2626" : "var(--ink)" }}>
                        {p.value} {p.unit}
                      </strong>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      <MedicalDisclaimer />
    </div>
  );
}
