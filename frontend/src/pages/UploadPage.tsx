import React, { useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  UploadCloud,
  FileText,
  CheckCircle2,
  AlertCircle,
  Clock,
  ArrowRight,
  ShieldCheck,
  RefreshCw,
} from 'lucide-react';
import api from '../services/api';
import MascotBadge from '../components/common/MascotBadge';

export const UploadPage: React.FC = () => {
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [documentType, setDocumentType] = useState('lab_report');
  const [documentTitle, setDocumentTitle] = useState('');
  const [testDate, setTestDate] = useState('');

  const [isUploading, setIsUploading] = useState(false);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [activeDocId, setActiveDocId] = useState<string | null>(null);
  const [jobProgress, setJobProgress] = useState(0);
  const [jobStage, setJobStage] = useState<string>('idle');
  const [jobMessage, setJobMessage] = useState<string>('');
  const [uploadError, setUploadError] = useState<string | null>(null);

  const stages = [
    { key: 'queued', label: 'Received' },
    { key: 'text_acquisition', label: 'Text Extraction' },
    { key: 'field_extraction', label: 'Field Extraction' },
    { key: 'rule_evaluation', label: 'Range Check' },
    { key: 'completed', label: 'Saved' },
  ];

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setSelectedFile(file);
      if (!documentTitle) {
        setDocumentTitle(file.name.replace(/\.[^/.]+$/, ''));
      }
    }
  };

  const pollJob = async (jobId: string, docId: string) => {
    const interval = setInterval(async () => {
      try {
        const job = await api.getJobStatus(jobId);
        setJobProgress(job.progressPercent);
        setJobStage(job.stage);
        setJobMessage(job.safeMessage);

        if (job.status === 'completed') {
          clearInterval(interval);
          setIsUploading(false);
          // Navigate to record detail after short completion pause
          setTimeout(() => {
            navigate(`/app/records/${docId}`);
          }, 1000);
        } else if (job.status === 'failed') {
          clearInterval(interval);
          setIsUploading(false);
          setUploadError('Document analysis could not be completed. Please review the file format.');
        }
      } catch (err) {
        clearInterval(interval);
        setIsUploading(false);
        setUploadError('Unable to poll analysis status.');
      }
    }, 1200);
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) return;

    setUploadError(null);
    setIsUploading(true);
    setJobStage('queued');
    setJobProgress(10);
    setJobMessage('Uploading file to secure storage...');

    try {
      const res = await api.uploadDocument(
        selectedFile,
        documentType,
        documentTitle || selectedFile.name,
        testDate || undefined
      );

      setActiveJobId(res.jobId);
      setActiveDocId(res.documentId);
      pollJob(res.jobId, res.documentId);
    } catch (err: unknown) {
      setIsUploading(false);
      setUploadError(err instanceof Error ? err.message : 'Upload failed.');
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-8">
      {/* ── Page Header ───────────────────────────────────────────── */}
      <div>
        <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight text-[#292443]">
          Upload Medical Document
        </h1>
        <p className="mt-1 text-sm text-[#77758A]">
          Upload your blood report, urine panel, or prescription. Text and measurements will be extracted and verified.
        </p>
      </div>

      {uploadError && (
        <div className="p-4 rounded-xl bg-red-50 border border-red-200 text-xs text-[#C93636] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{uploadError}</span>
          </div>
          <button
            onClick={() => setUploadError(null)}
            className="text-xs font-semibold underline ml-4 hover:text-red-800"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* ── Processing Tracker (Visible while running) ────────────── */}
      {isUploading && (
        <div className="bg-white p-6 rounded-2xl border border-[#E8E7F0] shadow-sm space-y-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-[#F0EEFF] text-[#6257F5] flex items-center justify-center">
                <Clock className="w-5 h-5 animate-spin" />
              </div>
              <div>
                <h3 className="font-bold text-sm text-[#292443]">Analysing Medical Document</h3>
                <p className="text-xs text-[#77758A]">{jobMessage || 'Executing AI/ML pipeline...'}</p>
              </div>
            </div>
            <span className="text-xs font-bold text-[#6257F5] bg-[#F0EEFF] px-2.5 py-1 rounded-full">
              {jobProgress}%
            </span>
          </div>

          {/* Progress Bar */}
          <div className="w-full bg-[#E8E7F0] h-2 rounded-full overflow-hidden">
            <div
              className="bg-[#6257F5] h-full transition-all duration-300 rounded-full"
              style={{ width: `${jobProgress}%` }}
            />
          </div>

          {/* 5-Stage Stepper */}
          <div className="grid grid-cols-5 gap-2 text-center text-xs">
            {stages.map((stage, idx) => {
              const stageIdx = stages.findIndex((s) => s.key === jobStage);
              const isPast = idx < stageIdx || jobStage === 'completed';
              const isCurrent = sIndex(jobStage, idx);

              function sIndex(current: string, i: number) {
                if (current === 'queued' && i === 0) return true;
                if (current === 'text_acquisition' && i === 1) return true;
                if (current === 'field_extraction' && i === 2) return true;
                if (current === 'rule_evaluation' && i === 3) return true;
                if (current === 'completed' && i === 4) return true;
                return false;
              }

              return (
                <div key={stage.key} className="space-y-1">
                  <div
                    className={`w-6 h-6 rounded-full mx-auto flex items-center justify-center text-[10px] font-bold transition-all ${
                      isPast
                        ? 'bg-emerald-500 text-white'
                        : isCurrent
                        ? 'bg-[#6257F5] text-white ring-4 ring-[#F0EEFF]'
                        : 'bg-slate-100 text-[#77758A]'
                    }`}
                  >
                    {isPast ? '✓' : idx + 1}
                  </div>
                  <p
                    className={`text-[11px] font-medium truncate ${
                      isCurrent ? 'text-[#6257F5] font-bold' : isPast ? 'text-[#292443]' : 'text-[#77758A]'
                    }`}
                  >
                    {stage.label}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ── Main Upload Form ──────────────────────────────────────── */}
      {!isUploading && (
        <form onSubmit={handleUpload} className="bg-white p-6 md:p-8 rounded-2xl border border-[#E8E7F0] shadow-sm space-y-6">
          {/* Dropzone */}
          <div
            onClick={() => fileInputRef.current?.click()}
            className="border-2 border-dashed border-[#E8E7F0] hover:border-[#6257F5] bg-[#F7F7FB] hover:bg-[#F0EEFF]/10 rounded-2xl p-8 text-center cursor-pointer transition select-none group"
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,image/png,image/jpeg,image/webp"
              onChange={handleFileChange}
              className="hidden"
            />
            <div className="w-14 h-14 rounded-2xl bg-white border border-[#E8E7F0] text-[#6257F5] flex items-center justify-center mx-auto mb-4 group-hover:scale-105 transition shadow-sm">
              <UploadCloud className="w-7 h-7" />
            </div>

            {selectedFile ? (
              <div className="space-y-1">
                <p className="text-sm font-bold text-[#292443] flex items-center justify-center gap-2">
                  <FileText className="w-4 h-4 text-[#6257F5]" />
                  <span>{selectedFile.name}</span>
                </p>
                <p className="text-xs text-[#77758A]">
                  {(selectedFile.size / 1024 / 1024).toFixed(2)} MB • Ready to analyze
                </p>
                <span className="inline-block mt-2 text-xs text-[#6257F5] font-semibold underline">
                  Change file
                </span>
              </div>
            ) : (
              <div className="space-y-1">
                <p className="text-sm font-bold text-[#292443]">
                  Drag and drop your medical report here, or <span className="text-[#6257F5]">browse</span>
                </p>
                <p className="text-xs text-[#77758A]">
                  Supported formats: PDF, PNG, JPG, WebP (up to 20MB)
                </p>
              </div>
            )}
          </div>

          {/* Form Options */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-semibold text-[#292443] mb-1.5">
                Document Type
              </label>
              <select
                value={documentType}
                onChange={(e) => setDocumentType(e.target.value)}
                className="w-full px-3 py-2.5 rounded-xl border border-[#E8E7F0] text-xs focus:border-[#6257F5] bg-white font-medium"
              >
                <option value="lab_report">Laboratory Report</option>
                <option value="prescription">Prescription</option>
                <option value="imaging_report">Imaging / Radiology</option>
                <option value="discharge_summary">Discharge Summary</option>
                <option value="other">Other Medical Document</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-[#292443] mb-1.5">
                Report Title (Optional)
              </label>
              <input
                type="text"
                value={documentTitle}
                onChange={(e) => setDocumentTitle(e.target.value)}
                placeholder="e.g. Annual Blood Work"
                className="w-full px-3 py-2 rounded-xl border border-[#E8E7F0] text-xs focus:border-[#6257F5] bg-white"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-[#292443] mb-1.5">
                Test Date (Optional)
              </label>
              <input
                type="date"
                value={testDate}
                onChange={(e) => setTestDate(e.target.value)}
                className="w-full px-3 py-2 rounded-xl border border-[#E8E7F0] text-xs focus:border-[#6257F5] bg-white"
              />
            </div>
          </div>

          {/* Submit Action */}
          <div className="pt-2 flex items-center justify-between border-t border-[#E8E7F0]">
            <div className="flex items-center gap-1.5 text-xs text-[#77758A]">
              <ShieldCheck className="w-4 h-4 text-[#22B8B0]" />
              <span>Encrypted at rest • Scoped strictly to your account</span>
            </div>

            <button
              type="submit"
              disabled={!selectedFile}
              className="px-6 py-2.5 rounded-xl bg-[#6257F5] hover:bg-[#5148d4] text-white text-xs font-semibold shadow-md shadow-violet-500/25 transition flex items-center gap-2 disabled:opacity-40"
            >
              <span>Upload & Analyse</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </form>
      )}
    </div>
  );
};

export default UploadPage;

