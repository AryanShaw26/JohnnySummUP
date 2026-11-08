import { useEffect, useState } from "react";
import { AlertTriangle, Clock, Eye } from "lucide-react";
import { Link } from "react-router-dom";
import { EmptyState } from "../../components/medical/EmptyState";
import { MedicalDisclaimer } from "../../components/medical/MedicalDisclaimer";
import { ReportStatusBadge } from "../../components/medical/ReportStatusBadge";
import { medicalApi } from "../../services/medicalApi";
import type { TimelineItem } from "../../types/medical";

export function ReportTimelinePage() {
  const [items, setItems] = useState<TimelineItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchTimeline = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await medicalApi.getTimeline();
        setItems(res);
      } catch (err: any) {
        setError(err?.message || "Failed to load report timeline");
      } finally {
        setLoading(false);
      }
    };
    fetchTimeline();
  }, []);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div>
        <p className="eyebrow" style={{ color: "var(--purple)", marginBottom: 6 }}>
          HISTORY
        </p>
        <h2 style={{ fontSize: 24, margin: "0 0 4px" }}>Report Timeline</h2>
        <p style={{ color: "var(--muted)", fontSize: 13, margin: 0 }}>
          A chronological view of your medical reports and key health findings over time.
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
      ) : items.length === 0 ? (
        <EmptyState
          icon={Clock}
          title="No timeline events recorded"
          description="Upload medical reports to start visualizing your health history along a timeline."
          actionText="Upload First Report"
          actionLink="/app/medical/documents/upload"
        />
      ) : (
        <div className="timeline-container">
          {items.map((item) => {
            const dateStr = new Date(item.report_date).toLocaleDateString(undefined, {
              month: "short",
              day: "numeric",
              year: "numeric",
            });

            return (
              <div key={item.document_id} className="timeline-node">
                <div className="timeline-node__dot" />
                <div className="timeline-card">
                  <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
                      <span style={{ fontSize: 13, fontWeight: 800, color: "var(--purple)" }}>
                        {dateStr}
                      </span>
                      <span className="badge badge--purple">
                        {item.document_type.replace("_", " ").toUpperCase()}
                      </span>
                      <ReportStatusBadge status={item.status} />
                      {item.flag_count > 0 && (
                        <span className="badge badge--red" style={{ gap: 4 }}>
                          <AlertTriangle size={12} />
                          <span>{item.flag_count} Flag{item.flag_count > 1 ? "s" : ""}</span>
                        </span>
                      )}
                    </div>

                    <Link
                      to={`/app/medical/documents/${item.document_id}`}
                      style={{ fontSize: 16, fontWeight: 700, color: "var(--ink)", textDecoration: "none" }}
                    >
                      {item.report_name}
                    </Link>

                    {/* Key Measurements Preview */}
                    {item.key_measurements.length > 0 && (
                      <div style={{ display: "flex", gap: 14, flexWrap: "wrap", marginTop: 4 }}>
                        {item.key_measurements.map((m, idx) => (
                          <div
                            key={idx}
                            style={{
                              padding: "4px 10px",
                              borderRadius: 8,
                              background: "#f7f5fb",
                              fontSize: 12,
                              color: "#463d59",
                            }}
                          >
                            <span style={{ color: "var(--muted)" }}>{m.name}: </span>
                            <strong>{m.value} {m.unit}</strong>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  <div>
                    <Link
                      to={`/app/medical/documents/${item.document_id}`}
                      className="button button--quiet"
                      style={{
                        border: "1px solid var(--border)",
                        borderRadius: 8,
                        padding: "8px 14px",
                        fontSize: 12,
                        display: "inline-flex",
                        alignItems: "center",
                        gap: 6,
                      }}
                    >
                      <Eye size={14} />
                      <span>View</span>
                    </Link>
                  </div>
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
