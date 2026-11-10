import { useRef, useState } from "react";
import {
  AlertCircle,
  FileCheck,
  FileText,
  FlaskConical,
  Pill,
  TestTube2,
  UploadCloud,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import { MedicalDisclaimer } from "../../components/medical/MedicalDisclaimer";
import { medicalApi } from "../../services/medicalApi";
import type { DocumentType } from "../../types/medical";

interface CategoryOption {
  id: string;
  docType: DocumentType;
  label: string;
  icon: any;
}

const CATEGORIES: CategoryOption[] = [
  { id: "prescription", docType: "prescription", label: "Prescription", icon: Pill },
  { id: "blood_test", docType: "laboratory_report", label: "Blood Test", icon: FlaskConical },
  { id: "urine_test", docType: "laboratory_report", label: "Urine Test", icon: TestTube2 },
  { id: "urea_test", docType: "laboratory_report", label: "Urea Test", icon: FlaskConical },
  { id: "other", docType: "other", label: "Other Report", icon: FileText },
];

export function UploadReportPage() {
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const uploadInFlightRef = useRef(false);

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<string>("blood_test");
  const [reportDate, setReportDate] = useState<string>("");
  const [uploading, setUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const validateFile = (file: File): boolean => {
    const validExtensions = [".pdf", ".jpg", ".jpeg", ".png"];
    const ext = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();
    if (!validExtensions.includes(ext)) {
      setError(`Unsupported file format. Please upload a PDF, JPG, or PNG file.`);
      return false;
    }
    if (file.size > 10 * 1024 * 1024) {
      setError("File exceeds maximum allowed size of 10 MB.");
      return false;
    }
    setError(null);
    return true;
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      if (validateFile(file)) {
        setSelectedFile(file);
      }
    }
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      if (validateFile(file)) {
        setSelectedFile(file);
      }
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (uploadInFlightRef.current) return;
    if (!selectedFile) {
      setError("Please select a file to upload.");
      return;
    }

    uploadInFlightRef.current = true;
    const catObj = CATEGORIES.find((c) => c.id === selectedCategory);
    const docType: DocumentType = catObj ? catObj.docType : "laboratory_report";

    setUploading(true);
    setError(null);

    try {
      const uploadedDoc = await medicalApi.uploadDocument(
        selectedFile,
        docType,
        reportDate || undefined
      );
      // Navigate directly to the newly uploaded document's detail/summary view
      navigate(`/app/medical/documents/${uploadedDoc.id}`);
    } catch (err: any) {
      setError(err?.message || "Failed to upload document. Please try again.");
      setUploading(false);
      uploadInFlightRef.current = false;
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24, maxWidth: 880, margin: "0 auto" }}>
      <div>
        <p className="eyebrow" style={{ color: "var(--purple)", marginBottom: 6 }}>
          DOCUMENTS
        </p>
        <h2 style={{ fontSize: 24, margin: "0 0 6px" }}>Upload Medical Document</h2>
        <p style={{ color: "var(--muted)", fontSize: 13, margin: 0 }}>
          Upload prescriptions, lab reports, or other medical documents for AI analysis.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="upload-card">
        {error && (
          <div className="form-alert" style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <AlertCircle size={18} className="flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Drag & Drop Zone */}
        <div
          className={`dropzone ${dragActive ? "dropzone--active" : ""}`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          role="button"
          tabIndex={0}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.jpg,.jpeg,.png"
            style={{ display: "none" }}
            onChange={handleFileChange}
            disabled={uploading}
          />
          <div className="dropzone__icon">
            <UploadCloud size={32} />
          </div>

          {selectedFile ? (
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 6 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, color: "var(--purple)", fontWeight: 700 }}>
                <FileCheck size={18} />
                <span>{selectedFile.name}</span>
              </div>
              <span style={{ fontSize: 12, color: "var(--muted)" }}>
                {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB — Click to choose different file
              </span>
            </div>
          ) : (
            <>
              <div className="dropzone__title">
                Drag &amp; drop your file here <span>or click to browse</span>
              </div>
              <div className="dropzone__subtitle">
                Supported formats: PDF (with selectable text layer), JPG, PNG (Max 10 MB)
              </div>
            </>
          )}
        </div>

        {/* Document Category Selector */}
        <div>
          <label style={{ display: "block", fontSize: 12, fontWeight: 700, color: "#473e5b", marginBottom: 10 }}>
            SELECT DOCUMENT TYPE
          </label>
          <div className="category-selector">
            {CATEGORIES.map((cat) => {
              const Icon = cat.icon;
              const isSelected = selectedCategory === cat.id;
              return (
                <button
                  key={cat.id}
                  type="button"
                  className={`category-card ${isSelected ? "category-card--selected" : ""}`}
                  onClick={() => setSelectedCategory(cat.id)}
                  disabled={uploading}
                >
                  <div className="category-card__icon">
                    <Icon size={18} />
                  </div>
                  <span>{cat.label}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Optional Report Date */}
        <div style={{ maxWidth: 320 }}>
          <label style={{ display: "block", fontSize: 12, fontWeight: 700, color: "#473e5b", marginBottom: 8 }}>
            REPORT DATE (OPTIONAL)
          </label>
          <div className="field__control">
            <input
              type="date"
              value={reportDate}
              onChange={(e) => setReportDate(e.target.value)}
              disabled={uploading}
            />
          </div>
          <span style={{ fontSize: 11, color: "var(--muted)", marginTop: 4, display: "block" }}>
            Leave blank if date is printed on the document.
          </span>
        </div>

        {/* Submit Action */}
        <div style={{ display: "flex", alignItems: "center", gap: 14, paddingTop: 10, borderTop: "1px solid #f0edf6" }}>
          <button
            type="submit"
            className="button button--primary button--large"
            disabled={!selectedFile || uploading}
            style={{ minWidth: 180 }}
          >
            {uploading ? (
              <>
                <div className="spinner" style={{ width: 18, height: 18, borderWidth: 2 }} />
                <span>Processing &amp; Uploading...</span>
              </>
            ) : (
              <span>Upload &amp; Analyze</span>
            )}
          </button>
          {selectedFile && !uploading && (
            <button
              type="button"
              className="button button--quiet"
              onClick={() => setSelectedFile(null)}
            >
              Clear file
            </button>
          )}
        </div>
      </form>

      <MedicalDisclaimer />
    </div>
  );
}
