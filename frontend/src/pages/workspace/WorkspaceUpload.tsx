import {
  AlertCircle,
  FileCheck,
  RefreshCw,
  Sparkles,
  UploadCloud,
} from "lucide-react";
import { useRef, useState } from "react";
import { workspaceApi } from "../../services/workspaceApi";
import type { WorkspaceMeta } from "./WorkspaceConfig";

interface Props {
  meta: WorkspaceMeta;
  onUploadSuccess: (documentId: string) => void;
}

export function WorkspaceUpload({ meta, onUploadSuccess }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [subtype, setSubtype] = useState(meta.subtypes[0]?.value || "other");
  const [label, setLabel] = useState("");
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [progressStage, setProgressStage] = useState("");
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setError("Please select a document file to upload.");
      return;
    }

    setUploading(true);
    setError(null);
    setProgressStage("Validating format & storing securely...");

    try {
      setTimeout(() => setProgressStage("Extracting structured pages & OCR..."), 700);
      setTimeout(() => setProgressStage("Analyzing domain terms with Gemini AI..."), 1500);

      const created = await workspaceApi.uploadDocument(
        meta.backendSlug,
        file,
        subtype,
        label || file.name
      );

      setProgressStage("Analysis complete! Redirecting...");
      setTimeout(() => {
        onUploadSuccess(created.id);
      }, 500);
    } catch (err: any) {
      setError(err?.message || "Failed to process and analyze document. Please check format and try again.");
      setUploading(false);
    }
  };

  return (
    <div style={{ maxWidth: 720, margin: "0 auto", width: "100%" }}>
      <div className="card">
        <div className="card__header">
          <div>
            <h3 className="card__title">
              <UploadCloud size={20} style={{ color: meta.accentColor }} /> Upload to {meta.name}
            </h3>
            <p style={{ margin: "4px 0 0", fontSize: 13, color: "var(--muted)" }}>
              Upload contracts, statements, policies, transcripts, or official records.
            </p>
          </div>
        </div>

        {error && (
          <div
            style={{
              padding: "12px 16px",
              background: "#fee2e2",
              border: "1px solid #fca5a5",
              borderRadius: 10,
              color: "#991b1b",
              fontSize: 13.5,
              display: "flex",
              alignItems: "center",
              gap: 10,
              marginBottom: 20,
            }}
          >
            <AlertCircle size={18} />
            <span style={{ flex: 1 }}>{error}</span>
            <button
              onClick={() => setError(null)}
              style={{ background: "none", border: "none", cursor: "pointer", color: "#991b1b", fontWeight: 700 }}
            >
              Dismiss
            </button>
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          {/* Dropzone */}
          <div
            className={`dropzone ${isDragging ? "dropzone--active" : ""}`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => inputRef.current?.click()}
          >
            <input
              ref={inputRef}
              type="file"
              accept=".pdf,.docx,.doc,.jpg,.jpeg,.png"
              style={{ display: "none" }}
              onChange={handleFileChange}
              disabled={uploading}
            />
            <div className="dropzone__icon">
              {file ? <FileCheck size={28} /> : <UploadCloud size={28} />}
            </div>
            <div>
              {file ? (
                <div>
                  <p style={{ fontWeight: 700, fontSize: 15, color: "var(--ink)", margin: "0 0 4px" }}>
                    {file.name}
                  </p>
                  <p style={{ fontSize: 12, color: "var(--muted)", margin: 0 }}>
                    {(file.size / (1024 * 1024)).toFixed(2)} MB • Ready to analyze
                  </p>
                </div>
              ) : (
                <div>
                  <p style={{ fontWeight: 700, fontSize: 15, color: "var(--ink)", margin: "0 0 4px" }}>
                    Drag & drop your file here, or click to browse
                  </p>
                  <p style={{ fontSize: 12, color: "var(--muted)", margin: 0 }}>
                    Supports <strong>PDF, DOCX, JPG, PNG</strong> up to 20 MB
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Subtype Selection */}
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <label style={{ fontSize: 13, fontWeight: 700, color: "var(--ink)" }}>
              Document Type / Category
            </label>
            <select
              value={subtype}
              onChange={(e) => setSubtype(e.target.value)}
              disabled={uploading}
              style={{
                padding: "10px 14px",
                borderRadius: 10,
                border: "1px solid var(--border)",
                background: "#ffffff",
                fontSize: 14,
                color: "var(--ink)",
              }}
            >
              {meta.subtypes.map((st) => (
                <option key={st.value} value={st.value}>
                  {st.label} — {st.hint}
                </option>
              ))}
            </select>
          </div>

          {/* Optional Label */}
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <label style={{ fontSize: 13, fontWeight: 700, color: "var(--ink)" }}>
              Document Label / Friendly Title (Optional)
            </label>
            <input
              type="text"
              placeholder="e.g. Master Services Agreement 2026 or Fall Term Grade Card"
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              disabled={uploading}
              style={{
                padding: "10px 14px",
                borderRadius: 10,
                border: "1px solid var(--border)",
                fontSize: 14,
              }}
            />
          </div>

          {/* Progress / Status display during upload */}
          {uploading && (
            <div
              style={{
                padding: "16px",
                borderRadius: 12,
                background: "#f8f5fe",
                border: "1px solid #e9dff9",
                display: "flex",
                alignItems: "center",
                gap: 12,
              }}
            >
              <RefreshCw size={18} className="spin" style={{ color: "var(--purple)" }} />
              <div>
                <strong style={{ fontSize: 14, color: "var(--purple-dark)" }}>Processing Document</strong>
                <p style={{ margin: "2px 0 0", fontSize: 12, color: "#6b5d84" }}>{progressStage}</p>
              </div>
            </div>
          )}

          {/* Submit Button */}
          <div style={{ display: "flex", justifyContent: "flex-end", gap: 12 }}>
            <button
              type="submit"
              className="button button--primary button--large"
              disabled={!file || uploading}
              style={{ width: "100%" }}
            >
              {uploading ? (
                <>
                  <RefreshCw size={18} className="spin" /> Processing & Analyzing...
                </>
              ) : (
                <>
                  <Sparkles size={18} /> Ingest & Analyze Document
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
