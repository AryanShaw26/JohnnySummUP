import { useEffect, useState } from "react";
import { Activity, Calendar } from "lucide-react";
import { EmptyState } from "../../components/medical/EmptyState";
import { MedicalDisclaimer } from "../../components/medical/MedicalDisclaimer";
import { medicalApi } from "../../services/medicalApi";
import type { ParameterComparisonResponse } from "../../types/medical";

export function HistoricalAnalyticsPage() {
  const [data, setData] = useState<ParameterComparisonResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchHistory = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await medicalApi.getHistorical();
        setData(res);
      } catch (err: any) {
        setError(err?.message || "Failed to load historical analytics");
      } finally {
        setLoading(false);
      }
    };
    fetchHistory();
  }, []);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div>
        <p className="eyebrow" style={{ color: "var(--purple)", marginBottom: 6 }}>
          HEALTH ANALYTICS
        </p>
        <h2 style={{ fontSize: 24, margin: "0 0 4px" }}>Historical Analytics</h2>
        <p style={{ color: "var(--muted)", fontSize: 13, margin: 0 }}>
          Long-term aggregated measurements and parameter summaries across your test history.
        </p>
      </div>

      {loading ? (
        <div style={{ display: "flex", justifyContent: "center", padding: "60px 0" }}>
          <div className="spinner" />
        </div>
      ) : error ? (
        <div className="panel-card" style={{ textAlign: "center", padding: 30 }}>
          <p className="form-alert" style={{ marginBottom: 14 }}>{error}</p>
          <button type="button" onClick={() => window.location.reload()} className="button button--primary button--compact">
            Retry
          </button>
        </div>
      ) : !data || data.rows.length === 0 ? (
        <EmptyState
          icon={Activity}
          title="No historical measurements recorded"
          description="Upload multiple lab reports over time to view long-term analytics and aggregate statistics."
          actionText="Upload Report"
          actionLink="/app/medical/documents/upload"
        />
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          {/* Summary metrics */}
          <div className="medical-stats-grid">
            <div className="stat-card">
              <div className="stat-card__icon stat-card__icon--purple">
                <Activity size={22} />
              </div>
              <div className="stat-card__info">
                <span className="stat-card__count">{data.rows.length}</span>
                <span className="stat-card__label">Unique Parameters</span>
              </div>
            </div>

            <div className="stat-card">
              <div className="stat-card__icon stat-card__icon--blue">
                <Calendar size={22} />
              </div>
              <div className="stat-card__info">
                <span className="stat-card__count">{data.report_dates.length}</span>
                <span className="stat-card__label">Test Sessions Recorded</span>
              </div>
            </div>
          </div>

          {/* Historical table */}
          <div className="panel-card">
            <h3 style={{ margin: "0 0 16px", fontSize: 17 }}>Historical Measurements Summary</h3>
            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Parameter Name</th>
                    <th>Unit</th>
                    <th>Stated Reference Range</th>
                    <th>Latest Value</th>
                    <th>First Value</th>
                    <th>Overall Trend</th>
                  </tr>
                </thead>
                <tbody>
                  {data.rows.map((row) => {
                    const nonNull = Object.entries(row.values_by_date)
                      .filter(([_, v]) => v !== null)
                      .map(([_, v]) => v as number);
                    const firstVal = nonNull[0] ?? "—";
                    const latestVal = nonNull[nonNull.length - 1] ?? "—";

                    return (
                      <tr key={row.parameter_name}>
                        <td style={{ fontWeight: 600 }}>{row.parameter_name}</td>
                        <td>{row.unit}</td>
                        <td style={{ color: "var(--muted)" }}>
                          {row.reference_range || "Not supplied"}
                        </td>
                        <td style={{ fontWeight: 700, color: "var(--purple)" }}>
                          {latestVal}
                        </td>
                        <td style={{ color: "var(--muted)" }}>{firstVal}</td>
                        <td>
                          <span
                            className={`badge ${
                              row.trend_direction === "up"
                                ? "badge--purple"
                                : row.trend_direction === "down"
                                ? "badge--blue"
                                : "badge--gray"
                            }`}
                          >
                            {row.trend_direction.toUpperCase()}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      <MedicalDisclaimer />
    </div>
  );
}
