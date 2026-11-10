import { useEffect, useState } from "react";
import { AlertTriangle, CheckCircle2, FileText } from "lucide-react";
import { Link } from "react-router-dom";
import { EmptyState } from "../../components/medical/EmptyState";
import { MedicalDisclaimer } from "../../components/medical/MedicalDisclaimer";
import { medicalApi } from "../../services/medicalApi";
import type { AbnormalityFlag } from "../../types/medical";

export function AbnormalityFlagsPage() {
  const [flags, setFlags] = useState<AbnormalityFlag[]>([]);
  const [loading, setLoading] = useState(true);
  const [severityFilter, setSeverityFilter] = useState<string>("all");
  const [error, setError] = useState<string | null>(null);

  const fetchFlags = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await medicalApi.getFlags({
        severity: severityFilter !== "all" ? severityFilter : undefined,
      });
      setFlags(res);
    } catch (err: any) {
      setError(err?.message || "Failed to load abnormality flags.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFlags();
  }, [severityFilter]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div>
        <p className="eyebrow" style={{ color: "var(--purple)", marginBottom: 6 }}>
          AI ANALYSIS
        </p>
        <h2 style={{ fontSize: 24, margin: "0 0 4px" }}>Abnormality Flags</h2>
        <p style={{ color: "var(--muted)", fontSize: 13, margin: 0 }}>
          Parameters that are outside the normal reference range or need clinical attention.
        </p>
      </div>

      {/* Header Banner if flags exist */}
      {flags.length > 0 && (
        <div
          style={{
            padding: "18px 24px",
            borderRadius: 14,
            background: "#fff5f5",
            border: "1px solid #fed7d7",
            display: "flex",
            alignItems: "center",
            gap: 14,
            color: "#991b1b",
          }}
        >
          <AlertTriangle size={24} className="flex-shrink-0" />
          <div>
            <strong style={{ fontSize: 15, display: "block", marginBottom: 2 }}>
              {flags.length} Abnormal Finding{flags.length > 1 ? "s" : ""} Detected
            </strong>
            <span style={{ fontSize: 12, color: "#7f1d1d" }}>
              Review these parameters and consider consulting a qualified healthcare professional.
            </span>
          </div>
        </div>
      )}

      {/* Severity Filter */}
      <div className="panel-card" style={{ padding: "12px 18px", display: "flex", justifyContent: "flex-end" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ fontSize: 12, color: "var(--muted)" }}>Filter by severity:</span>
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="button button--quiet"
            style={{
              border: "1px solid var(--border)",
              borderRadius: 8,
              padding: "6px 12px",
              fontSize: 12,
              background: "#fff",
            }}
          >
            <option value="all">All Severities</option>
            <option value="high">High</option>
            <option value="review">Review</option>
            <option value="info">Info</option>
          </select>
        </div>
      </div>

      {/* Flags List */}
      {loading ? (
        <div style={{ display: "flex", justifyContent: "center", padding: "60px 0" }}>
          <div className="spinner" />
        </div>
      ) : error ? (
        <div className="panel-card" style={{ textAlign: "center", padding: 30 }}>
          <p className="form-alert" style={{ marginBottom: 14 }}>{error}</p>
          <button type="button" onClick={fetchFlags} className="button button--primary button--compact">
            Retry
          </button>
        </div>
      ) : flags.length === 0 ? (
        <EmptyState
          icon={CheckCircle2}
          title="No abnormal flags found"
          description="None of your uploaded reports currently show out-of-range parameters."
          actionText="Upload New Report"
          actionLink="/app/medical/documents/upload"
        />
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {flags.map((flag) => {
            const isHigh = flag.severity === "high";
            const badgeLabel =
              flag.flag_type === "above_range"
                ? isHigh ? "High" : "Slightly High"
                : flag.flag_type === "below_range"
                ? isHigh ? "Low" : "Slightly Low"
                : "Needs Review";

            return (
              <div key={flag.id} className="flag-card" style={{ padding: "20px 24px" }}>
                <div className="flag-card__left" style={{ gap: 16 }}>
                  <div
                    className="flag-card__icon"
                    style={{
                      background: isHigh ? "#fef2f2" : "#fff8eb",
                      color: isHigh ? "#dc2626" : "#d97706",
                      width: 44,
                      height: 44,
                      borderRadius: 12,
                    }}
                  >
                    <AlertTriangle size={22} />
                  </div>
                  <div className="flag-card__details">
                    <strong style={{ fontSize: 16, marginBottom: 4 }}>
                      {flag.parameter_name}
                    </strong>
                    <div style={{ fontSize: 13, color: "#4b435d", marginBottom: 6 }}>
                      <span>Your Value: </span>
                      <strong style={{ color: isHigh ? "#dc2626" : "var(--purple)" }}>
                        {flag.observed_value !== null ? `${flag.observed_value} ${flag.unit || ""}` : "Out of range"}
                      </strong>
                      {flag.reference_text && (
                        <span style={{ marginLeft: 12, color: "var(--muted)" }}>
                          Normal Range: {flag.reference_text}
                        </span>
                      )}
                    </div>
                    {flag.explanation && (
                      <p style={{ margin: "4px 0 8px", fontSize: 12, color: "#6b7280", lineHeight: 1.5 }}>
                        {flag.explanation}
                      </p>
                    )}
                    <Link
                      to={`/app/medical/documents/${flag.document_id}`}
                      style={{
                        color: "var(--purple)",
                        fontSize: 12,
                        fontWeight: 600,
                        display: "inline-flex",
                        alignItems: "center",
                        gap: 5,
                      }}
                    >
                      <FileText size={13} />
                      <span>{flag.document_name || "View Source Report"}</span>
                    </Link>
                  </div>
                </div>

                <div>
                  <span className={`badge ${isHigh ? "badge--red" : "badge--amber"}`} style={{ fontSize: 12, padding: "6px 14px" }}>
                    {badgeLabel}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}

      <MedicalDisclaimer />
    </div>
  );
}
