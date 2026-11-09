import { useEffect, useState } from "react";
import { ArrowDown, ArrowUp, Columns3, Minus } from "lucide-react";
import { EmptyState } from "../../components/medical/EmptyState";
import { MedicalDisclaimer } from "../../components/medical/MedicalDisclaimer";
import { medicalApi } from "../../services/medicalApi";
import type { ParameterComparisonResponse } from "../../types/medical";

export function ParameterComparisonPage() {
  const [data, setData] = useState<ParameterComparisonResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchComparison = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await medicalApi.getComparison();
      setData(res);
    } catch (err: any) {
      setError(err?.message || "Failed to load parameter comparison");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchComparison();
  }, []);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div>
        <p className="eyebrow" style={{ color: "var(--purple)", marginBottom: 6 }}>
          HEALTH ANALYTICS
        </p>
        <h2 style={{ fontSize: 24, margin: "0 0 4px" }}>Parameter Comparison</h2>
        <p style={{ color: "var(--muted)", fontSize: 13, margin: 0 }}>
          Compare key health parameters across multiple reports in a side-by-side matrix.
        </p>
      </div>

      {loading ? (
        <div style={{ display: "flex", justifyContent: "center", padding: "60px 0" }}>
          <div className="spinner" />
        </div>
      ) : error ? (
        <div className="panel-card" style={{ textAlign: "center", padding: 30 }}>
          <p className="form-alert" style={{ marginBottom: 14 }}>{error}</p>
          <button type="button" onClick={fetchComparison} className="button button--primary button--compact">
            Retry
          </button>
        </div>
      ) : !data || data.rows.length === 0 ? (
        <EmptyState
          icon={Columns3}
          title="No comparison data available"
          description="Upload multiple laboratory reports over time to compare health parameters side-by-side."
          actionText="Upload Report"
          actionLink="/app/medical/documents/upload"
        />
      ) : (
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th style={{ minWidth: 200 }}>Parameter</th>
                {data.report_dates.map((d) => (
                  <th key={d} style={{ textAlign: "center" }}>
                    {new Date(d).toLocaleDateString(undefined, {
                      month: "short",
                      year: "numeric",
                    })}
                  </th>
                ))}
                <th style={{ textAlign: "center", width: 90 }}>Trend</th>
              </tr>
            </thead>
            <tbody>
              {data.rows.map((row) => (
                <tr key={row.parameter_name}>
                  <td>
                    <strong style={{ color: "var(--ink)", display: "block" }}>
                      {row.parameter_name}
                    </strong>
                    <span style={{ fontSize: 11, color: "var(--muted)" }}>
                      {row.unit} {row.reference_range ? `• Range: ${row.reference_range}` : ""}
                    </span>
                  </td>

                  {data.report_dates.map((d) => {
                    const val = row.values_by_date[d];
                    return (
                      <td key={d} style={{ textAlign: "center", fontWeight: 600 }}>
                        {val !== null && val !== undefined ? val : "—"}
                      </td>
                    );
                  })}

                  <td style={{ textAlign: "center" }}>
                    {row.trend_direction === "up" ? (
                      <span title="Increasing trend" style={{ color: "var(--purple)", display: "inline-flex" }}>
                        <ArrowUp size={16} />
                      </span>
                    ) : row.trend_direction === "down" ? (
                      <span title="Decreasing trend" style={{ color: "#2563eb", display: "inline-flex" }}>
                        <ArrowDown size={16} />
                      </span>
                    ) : (
                      <span title="Stable" style={{ color: "var(--muted)", display: "inline-flex" }}>
                        <Minus size={16} />
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <MedicalDisclaimer />
    </div>
  );
}
