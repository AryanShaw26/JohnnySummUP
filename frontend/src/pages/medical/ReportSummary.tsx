import { useEffect, useRef, useState } from "react";
import {
  AlertCircle,
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  Download,
  FileText,
  Info,
  RefreshCw,
  Sparkles,
  Trash2,
} from "lucide-react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { MedicalDisclaimer } from "../../components/medical/MedicalDisclaimer";
import { ReportStatusBadge } from "../../components/medical/ReportStatusBadge";
import { medicalApi } from "../../services/medicalApi";
import type { MedicalDocumentDetail } from "../../types/medical";

export function ReportSummaryPage() {
  const { documentId } = useParams<{ documentId: string }>();
  const navigate = useNavigate();

  const [document, setDocument] = useState<MedicalDocumentDetail | null>(null);
  const [activeTab, setActiveTab] = useState<"summary" | "findings" | "values" | "explanation">("summary");
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [retryProvider, setRetryProvider] = useState<"openai" | "gemini">("openai");

  const pollingRef = useRef<number | null>(null);

  const fetchDocument = async (showLoading = true) => {
    if (!documentId) return;
    if (showLoading) setLoading(true);
    setError(null);
    try {
      const data = await medicalApi.getDocumentDetails(documentId);
      setDocument(data);

      // Setup polling if status is processing or queued
      if (data.status === "processing" || data.status === "queued") {
        if (!pollingRef.current) {
          pollingRef.current = window.setInterval(async () => {
            try {
              const refreshed = await medicalApi.getDocumentDetails(documentId);
              setDocument(refreshed);
              if (refreshed.status !== "processing" && refreshed.status !== "queued") {
                if (pollingRef.current) {
                  clearInterval(pollingRef.current);
                  pollingRef.current = null;
                }
              }
            } catch {
              // ignore polling error
            }
          }, 2500);
        }
      } else if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    } catch (err: any) {
      setError(err?.message || "Failed to load report summary.");
    } finally {
      if (showLoading) setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocument(true);
    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    };
  }, [documentId]);

  const handleDownload = async () => {
    if (!document) return;
    try {
      await medicalApi.downloadDocument(document.id, document.original_filename);
    } catch {
      alert("Failed to download document file.");
    }
  };

  const handleDelete = async () => {
    if (!document) return;
    if (!window.confirm("Are you sure you want to delete this document?")) return;
    try {
      await medicalApi.deleteDocument(document.id);
      navigate("/app/medical/documents");
    } catch (err: any) {
      alert(err?.message || "Failed to delete document.");
    }
  };

  const handleReanalyze = async () => {
    if (!document) return;
    setAnalyzing(true);
    setStatusMessage(null);
    try {
      const result = await medicalApi.analyzeDocument(document.id, retryProvider);
      if (result.status === "failed") {
        setStatusMessage(result.error_message || "Analysis failed. Please check the error details below.");
      } else if (result.status === "completed") {
        setStatusMessage("Analysis completed successfully!");
      }
      await fetchDocument(false);
    } catch (err: any) {
      setStatusMessage(err?.message || "Failed to re-run AI analysis.");
    } finally {
      setAnalyzing(false);
    }
  };

  if (loading) {
    return (
      <div style={{ display: "flex", justifyContent: "center", padding: "60px 0" }}>
        <div className="spinner" />
      </div>
    );
  }

  if (error || !document) {
    return (
      <div className="panel-card" style={{ textAlign: "center", padding: 40 }}>
        <p className="form-alert" style={{ marginBottom: 16 }}>{error || "Report not found"}</p>
        <Link to="/app/medical/documents" className="button button--primary button--compact">
          Back to Documents
        </Link>
      </div>
    );
  }

  const latestAnalysis = document.analyses && document.analyses.length > 0 ? document.analyses[0] : null;
  const isFailed = document.status === "failed" || latestAnalysis?.status === "failed";
  const isProcessing = document.status === "processing" || latestAnalysis?.status === "processing";
  const isUnavailable = document.status === "analysis_unavailable" || latestAnalysis?.status === "unavailable";
  const isCompleted = document.status === "completed" || latestAnalysis?.status === "completed";

  const failureMessage =
    latestAnalysis?.error_message ||
    document.failure_message ||
    "An error occurred while analyzing this medical document.";
  const failureCode = latestAnalysis?.error_code || document.failure_code;

  const repDate = document.report_date
    ? new Date(document.report_date).toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
        year: "numeric",
      })
    : new Date(document.created_at).toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
        year: "numeric",
      });

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      {/* Back Link */}
      <div>
        <Link to="/app/medical/documents" className="back-link">
          <ArrowLeft size={15} /> Back to All Reports
        </Link>
      </div>

      {/* Action status toast if any */}
      {statusMessage && (
        <div
          className={`form-alert ${isFailed ? "" : "badge--green"}`}
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            background: isFailed ? "#fff5f5" : "#ecfdf5",
            borderColor: isFailed ? "#fecaca" : "#a7f3d0",
            color: isFailed ? "#991b1b" : "#065f46",
          }}
        >
          <span>{statusMessage}</span>
          <button
            type="button"
            className="button button--quiet"
            style={{ padding: "2px 8px", fontSize: 11 }}
            onClick={() => setStatusMessage(null)}
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Report Identity Card */}
      <div className="panel-card" style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 14 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
            <div
              style={{
                width: 48,
                height: 48,
                borderRadius: 14,
                background: "#f0e9fb",
                color: "var(--purple)",
                display: "grid",
                placeItems: "center",
              }}
            >
              <FileText size={24} />
            </div>
            <div>
              <h2 style={{ fontSize: 20, margin: "0 0 4px", color: "var(--ink)" }}>
                {document.original_filename}
              </h2>
              <div style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 12, color: "var(--muted)" }}>
                <span className="badge badge--purple">
                  {document.document_type.replace("_", " ").toUpperCase()}
                </span>
                {latestAnalysis?.extraction_method && (
                  <span className="badge badge--gray">
                    {latestAnalysis.extraction_method === "ocr"
                      ? "OCR"
                      : latestAnalysis.extraction_method === "hybrid"
                      ? "Hybrid Text/OCR"
                      : "Digital PDF Text"}
                  </span>
                )}
                {latestAnalysis?.provider && (
                  <span className="badge badge--purple" style={{ textTransform: "capitalize" }}>
                    {latestAnalysis.provider} ({latestAnalysis.model_name || "default"})
                  </span>
                )}
                <span>Report Date: {repDate}</span>
                <span>•</span>
                <span>{(document.file_size_bytes / 1024).toFixed(1)} KB</span>
              </div>
            </div>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <ReportStatusBadge status={document.status} />
            <button
              type="button"
              className="action-btn"
              title="Download Original File"
              onClick={handleDownload}
            >
              <Download size={16} />
            </button>
            <button
              type="button"
              className="action-btn"
              title="Re-run AI Analysis"
              onClick={handleReanalyze}
              disabled={analyzing || isProcessing}
            >
              <RefreshCw size={16} className={analyzing || isProcessing ? "spinner" : ""} />
            </button>
            <button
              type="button"
              className="action-btn action-btn--danger"
              title="Delete Report"
              onClick={handleDelete}
            >
              <Trash2 size={16} />
            </button>
          </div>
        </div>

        {/* Tab Selection */}
        <div style={{ display: "flex", gap: 8, borderTop: "1px solid #f0edf6", paddingTop: 14 }}>
          {(["summary", "findings", "values", "explanation"] as const).map((tab) => {
            const labels = {
              summary: "Summary",
              findings: `Key Findings (${document.findings.length})`,
              values: `Values (${document.measurements.length})`,
              explanation: "Explanation",
            };
            return (
              <button
                key={tab}
                type="button"
                className={`medical-subnav__pill ${activeTab === tab ? "medical-subnav__pill--active" : ""}`}
                onClick={() => setActiveTab(tab)}
              >
                {labels[tab]}
              </button>
            );
          })}
        </div>
      </div>

      {/* Tab Content */}
      {activeTab === "summary" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {/* If Processing */}
          {isProcessing && (
            <div
              className="panel-card"
              style={{
                display: "flex",
                alignItems: "center",
                gap: 16,
                padding: "24px 28px",
                background: "#faf8fe",
                borderColor: "#e4d9f6",
              }}
            >
              <div className="spinner" style={{ width: 24, height: 24 }} />
              <div>
                <strong style={{ fontSize: 14, color: "var(--purple-dark)", display: "block" }}>
                  AI Analysis in Progress...
                </strong>
                <span style={{ fontSize: 12, color: "var(--muted)" }}>
                  Analyzing report text, extracting findings, and checking reference ranges.
                </span>
              </div>
            </div>
          )}

          {/* If Failed */}
          {isFailed && (
            <div
              className="panel-card"
              style={{
                display: "flex",
                flexDirection: "column",
                gap: 12,
                padding: "22px 26px",
                background: "#fff8f8",
                borderColor: "#fecaca",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 12, color: "#dc2626" }}>
                <AlertCircle size={22} className="flex-shrink-0" />
                <strong style={{ fontSize: 15 }}>
                  {failureCode && ["OCR_NO_TEXT", "OCR_NOT_CONFIGURED", "CORRUPT_DOCUMENT", "ENCRYPTED_DOCUMENT", "UNSUPPORTED_DOCUMENT", "extraction_empty"].includes(failureCode)
                    ? "Document Extraction Notice"
                    : "AI Analysis Notice"}
                </strong>
                {failureCode && (
                  <span className="badge badge--red" style={{ fontSize: 10, padding: "2px 8px" }}>
                    {failureCode}
                  </span>
                )}
              </div>
              <p style={{ margin: "2px 0 6px", fontSize: 13, color: "#7f1d1d", lineHeight: 1.6 }}>
                {failureMessage}
              </p>
              <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap", marginTop: 4 }}>
                <select
                  value={retryProvider}
                  onChange={(e) => setRetryProvider(e.target.value as "openai" | "gemini")}
                  className="input"
                  style={{ padding: "4px 8px", fontSize: 12, height: 32, width: "auto" }}
                >
                  <option value="openai">OpenAI (gpt-4o-mini)</option>
                  <option value="gemini">Gemini (gemini-1.5-flash)</option>
                </select>
                <button
                  type="button"
                  className="button button--primary button--compact"
                  onClick={handleReanalyze}
                  disabled={analyzing}
                  style={{ fontSize: 12 }}
                >
                  <RefreshCw size={13} className={analyzing ? "spinner" : ""} />
                  <span>{analyzing ? "Retrying..." : "Retry Analysis"}</span>
                </button>
              </div>
            </div>
          )}

          {/* If AI Not Configured */}
          {isUnavailable && !isFailed && (
            <div
              className="panel-card"
              style={{
                display: "flex",
                alignItems: "center",
                gap: 14,
                padding: "20px 24px",
                background: "#f9f8fc",
                borderColor: "#e9e4f3",
              }}
            >
              <Info size={22} style={{ color: "var(--purple)", flexShrink: 0 }} />
              <div>
                <strong style={{ fontSize: 14, color: "var(--ink)", display: "block" }}>
                  AI Analysis Unavailable
                </strong>
                <span style={{ fontSize: 12, color: "var(--muted)" }}>
                  {failureMessage}
                </span>
              </div>
            </div>
          )}

          {/* If Completed - AI Summary Card */}
          {isCompleted && latestAnalysis?.summary && (
            <div className="ai-summary-card">
              <div className="ai-summary-card__header">
                <Sparkles size={20} />
                <span>AI Summary</span>
              </div>
              <p className="ai-summary-card__text">
                {latestAnalysis.summary}
              </p>

              {/* Key Highlights */}
              {latestAnalysis.key_points && latestAnalysis.key_points.length > 0 && (
                <div style={{ marginTop: 8 }}>
                  <strong style={{ fontSize: 13, color: "var(--ink)", display: "block", marginBottom: 8 }}>
                    Key Highlights
                  </strong>
                  <div className="ai-highlights">
                    {latestAnalysis.key_points.map((pt: any, i: number) => (
                      <div key={i} className="ai-highlights__item">
                        <CheckCircle2 size={16} className="ai-highlights__check" />
                        <span>{typeof pt === "string" ? pt : JSON.stringify(pt)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Abnormality Flags on this report */}
          {document.flags.length > 0 && (
            <div className="panel-card" style={{ borderColor: "#fed7aa" }}>
              <div className="panel-card__header">
                <div style={{ display: "flex", alignItems: "center", gap: 8, color: "#c2410c" }}>
                  <AlertTriangle size={18} />
                  <h3 style={{ color: "#c2410c" }}>
                    {document.flags.length} Flagged Finding{document.flags.length > 1 ? "s" : ""}
                  </h3>
                </div>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {document.flags.map((flag) => (
                  <div key={flag.id} className="flag-card">
                    <div className="flag-card__left">
                      <div className="flag-card__icon" style={{ background: "#fef2f2", color: "#dc2626" }}>
                        <AlertTriangle size={18} />
                      </div>
                      <div className="flag-card__details">
                        <strong>{flag.parameter_name}</strong>
                        <span>
                          Observed: {flag.observed_value} {flag.unit || ""} (Stated Range: {flag.reference_text || "N/A"})
                        </span>
                        {flag.explanation && (
                          <div style={{ fontSize: 11, color: "#6b7280", marginTop: 4 }}>
                            {flag.explanation}
                          </div>
                        )}
                      </div>
                    </div>
                    <span className={`badge ${flag.severity === "high" ? "badge--red" : "badge--amber"}`}>
                      {flag.severity === "high" ? "High" : "Needs Review"}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {activeTab === "findings" && (
        <div className="panel-card">
          <div className="panel-card__header">
            <h3>Extracted Structured Findings</h3>
          </div>
          {document.findings.length === 0 ? (
            <p style={{ color: "var(--muted)", fontSize: 13, margin: 0 }}>
              No structured findings extracted from this document.
            </p>
          ) : (
            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Finding / Parameter</th>
                    <th>Category</th>
                    <th>Value</th>
                    <th>Reference Range</th>
                    <th>Confidence</th>
                  </tr>
                </thead>
                <tbody>
                  {document.findings.map((f) => (
                    <tr key={f.id}>
                      <td style={{ fontWeight: 600 }}>{f.name}</td>
                      <td>
                        <span className="badge badge--purple">{f.category}</span>
                      </td>
                      <td>
                        {f.value_text || (f.numeric_value !== null ? `${f.numeric_value} ${f.unit || ""}` : "Not found")}
                      </td>
                      <td style={{ color: "var(--muted)" }}>
                        {f.reference_text || "Not supplied in report"}
                      </td>
                      <td style={{ color: "var(--muted)", fontSize: 12 }}>
                        {f.confidence !== null && f.confidence !== undefined
                          ? `${Math.round(f.confidence * 100)}%`
                          : "N/A"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {activeTab === "values" && (
        <div className="panel-card">
          <div className="panel-card__header">
            <h3>Normalized Test Measurements</h3>
          </div>
          {document.measurements.length === 0 ? (
            <p style={{ color: "var(--muted)", fontSize: 13, margin: 0 }}>
              No numeric lab test measurements extracted from this document.
            </p>
          ) : (
            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Parameter Name</th>
                    <th>Measured Value</th>
                    <th>Unit</th>
                    <th>Reference Low</th>
                    <th>Reference High</th>
                    <th>Report Stated Range</th>
                  </tr>
                </thead>
                <tbody>
                  {document.measurements.map((m) => (
                    <tr key={m.id}>
                      <td style={{ fontWeight: 600 }}>{m.parameter_name}</td>
                      <td style={{ fontWeight: 700, color: "var(--purple)" }}>{m.numeric_value}</td>
                      <td>{m.unit}</td>
                      <td style={{ color: "var(--muted)" }}>{m.reference_low ?? "—"}</td>
                      <td style={{ color: "var(--muted)" }}>{m.reference_high ?? "—"}</td>
                      <td style={{ color: "var(--muted)" }}>{m.reference_text || "Not supplied"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {activeTab === "explanation" && (
        <div className="panel-card" style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <h3>Plain-Language Report Explanation</h3>
          <p style={{ fontSize: 14, lineHeight: 1.7, color: "#473d5e", margin: 0 }}>
            {latestAnalysis?.summary ||
              "This report was processed through our automated document pipeline. Values are extracted directly from the document file without altering source measurements."}
          </p>
          <div style={{ background: "#f9f8fc", padding: 16, borderRadius: 12, border: "1px solid #ebe5f5" }}>
            <h4 style={{ fontSize: 13, margin: "0 0 6px", color: "var(--ink)" }}>Understanding Reference Ranges</h4>
            <p style={{ fontSize: 12, color: "var(--muted)", margin: 0, lineHeight: 1.6 }}>
              Reference ranges vary by laboratory, equipment, and testing methodology. JohnnySummUP preserves only the reference ranges explicitly printed on your report. A value outside a laboratory reference range is not a medical diagnosis.
            </p>
          </div>
        </div>
      )}

      <MedicalDisclaimer />
    </div>
  );
}
