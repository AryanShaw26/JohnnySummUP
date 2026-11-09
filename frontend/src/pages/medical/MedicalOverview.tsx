import { useEffect, useState } from "react";
import {
  AlertTriangle,
  ChevronRight,
  FileText,
  FlaskConical,
  HeartPulse,
  Pill,
  Upload,
} from "lucide-react";
import { Link } from "react-router-dom";
import { EmptyState } from "../../components/medical/EmptyState";
import { MedicalDisclaimer } from "../../components/medical/MedicalDisclaimer";
import { ReportStatusBadge } from "../../components/medical/ReportStatusBadge";
import { medicalApi } from "../../services/medicalApi";
import type { MedicalOverview } from "../../types/medical";

export function MedicalOverviewPage() {
  const [data, setData] = useState<MedicalOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchOverview = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await medicalApi.getOverview();
      setData(res);
    } catch (err: any) {
      setError(err?.message || "Failed to load medical dashboard");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOverview();
  }, []);

  if (loading) {
    return (
      <div style={{ display: "flex", justifyContent: "center", padding: "60px 0" }}>
        <div className="spinner" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="panel-card" style={{ textAlign: "center", padding: 40 }}>
        <p className="form-alert" style={{ marginBottom: 16 }}>{error}</p>
        <button type="button" onClick={fetchOverview} className="button button--primary button--compact">
          Retry
        </button>
      </div>
    );
  }

  const overview = data || {
    total_reports: 0,
    prescriptions_count: 0,
    lab_reports_count: 0,
    important_findings_count: 0,
    recent_reports: [],
    important_findings: [],
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      {/* Hero Section */}
      <section className="medical-hero">
        <div className="medical-hero__content">
          <p className="eyebrow" style={{ color: "var(--purple)", marginBottom: 8 }}>
            MEDICAL WORKSPACE
          </p>
          <h2>Medical Dashboard</h2>
          <p>
            Upload, analyse and track your medical reports with AI-powered insights.
          </p>
          <div style={{ marginTop: 18 }}>
            <Link to="/app/medical/documents/upload" className="button button--primary button--compact">
              <Upload size={15} aria-hidden="true" />
              <span>Upload Report</span>
            </Link>
          </div>
        </div>
        <div className="medical-hero__art" aria-hidden="true">
          <HeartPulse size={42} />
        </div>
      </section>

      {/* 4 Summary Stat Cards */}
      <section className="medical-stats-grid" aria-label="Medical metrics summary">
        <div className="stat-card">
          <div className="stat-card__icon stat-card__icon--purple">
            <FileText size={22} aria-hidden="true" />
          </div>
          <div className="stat-card__info">
            <span className="stat-card__count">{overview.total_reports}</span>
            <span className="stat-card__label">Total Reports</span>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-card__icon stat-card__icon--blue">
            <Pill size={22} aria-hidden="true" />
          </div>
          <div className="stat-card__info">
            <span className="stat-card__count">{overview.prescriptions_count}</span>
            <span className="stat-card__label">Prescriptions</span>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-card__icon stat-card__icon--amber">
            <FlaskConical size={22} aria-hidden="true" />
          </div>
          <div className="stat-card__info">
            <span className="stat-card__count">{overview.lab_reports_count}</span>
            <span className="stat-card__label">Lab Reports</span>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-card__icon stat-card__icon--red">
            <AlertTriangle size={22} aria-hidden="true" />
          </div>
          <div className="stat-card__info">
            <span className="stat-card__count">{overview.important_findings_count}</span>
            <span className="stat-card__label">Important Findings</span>
          </div>
        </div>
      </section>

      {/* Panels: Recent Reports & Important Findings */}
      <section className="overview-grid">
        {/* Recent Reports Panel */}
        <div className="panel-card">
          <div className="panel-card__header">
            <h3>Recent Reports</h3>
            <Link to="/app/medical/documents" className="text-link" style={{ fontSize: 12 }}>
              View all <ChevronRight size={14} />
            </Link>
          </div>

          {overview.recent_reports.length === 0 ? (
            <EmptyState
              icon={FileText}
              title="No reports yet"
              description="Upload your prescriptions, blood tests, or other health documents to see insights here."
              actionText="Upload Report"
              actionLink="/app/medical/documents/upload"
            />
          ) : (
            <div className="table-container" style={{ border: "none" }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Report Name</th>
                    <th>Type</th>
                    <th>Date</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {overview.recent_reports.map((doc) => (
                    <tr key={doc.id}>
                      <td>
                        <Link
                          to={`/app/medical/documents/${doc.id}`}
                          style={{ fontWeight: 600, color: "var(--purple)" }}
                        >
                          {doc.original_filename}
                        </Link>
                      </td>
                      <td>
                        <span className="badge badge--purple">
                          {doc.document_type.replace("_", " ").toUpperCase()}
                        </span>
                      </td>
                      <td style={{ color: "#777085", fontSize: 12 }}>
                        {doc.report_date
                          ? new Date(doc.report_date).toLocaleDateString(undefined, {
                              month: "short",
                              day: "numeric",
                              year: "numeric",
                            })
                          : new Date(doc.created_at).toLocaleDateString(undefined, {
                              month: "short",
                              day: "numeric",
                              year: "numeric",
                            })}
                      </td>
                      <td>
                        <ReportStatusBadge status={doc.status} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Important Findings Panel */}
        <div className="panel-card">
          <div className="panel-card__header">
            <h3>Important Findings</h3>
            <Link to="/app/medical/analysis/flags" className="text-link" style={{ fontSize: 12 }}>
              View all <ChevronRight size={14} />
            </Link>
          </div>

          {overview.important_findings.length === 0 ? (
            <div style={{ textAlign: "center", padding: "30px 10px", color: "var(--muted)", fontSize: 13 }}>
              <AlertTriangle size={28} style={{ color: "#10b981", margin: "0 auto 10px" }} />
              <p style={{ margin: 0 }}>No abnormal findings detected in your current reports.</p>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {overview.important_findings.map((finding) => (
                <Link
                  key={finding.id}
                  to="/app/medical/analysis/flags"
                  className="flag-card"
                  style={{ textDecoration: "none" }}
                >
                  <div className="flag-card__left">
                    <div className="flag-card__icon" style={{ background: "#fef2f2", color: "#dc2626" }}>
                      <AlertTriangle size={18} />
                    </div>
                    <div className="flag-card__details">
                      <strong>{finding.parameter_name}</strong>
                      <span>
                        {finding.observed_value !== null ? `${finding.observed_value} ${finding.unit || ""}` : ""}
                        {finding.reference_text ? ` (Ref: ${finding.reference_text})` : ""}
                      </span>
                    </div>
                  </div>
                  <span
                    className={`badge ${
                      finding.severity === "high" ? "badge--red" : "badge--amber"
                    }`}
                  >
                    {finding.severity === "high" ? "High" : "Needs Review"}
                  </span>
                </Link>
              ))}
            </div>
          )}
        </div>
      </section>

      {/* Safety Disclaimer */}
      <MedicalDisclaimer />
    </div>
  );
}
