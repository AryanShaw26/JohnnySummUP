import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  FileText,
  Search,
  CheckCircle2,
  TrendingUp,
  ShieldCheck,
  ArrowRight,
  Sparkles,
  Lock,
  ChevronDown,
  Layers,
  FileCheck,
  HelpCircle,
} from 'lucide-react';
import MascotBadge from '../components/common/MascotBadge';

export const LandingPage: React.FC = () => {
  return (
    <div className="min-h-screen bg-[#F7F7FB] text-[#292443] flex flex-col font-sans">
      {/* ── Public Navbar ─────────────────────────────────────────── */}
      <header className="border-b border-[#E8E7F0] bg-white sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-6 h-18 flex items-center justify-between">
          <MascotBadge size="md" showTagline />

          <nav className="hidden md:flex items-center gap-8 text-sm font-medium text-[#77758A]">
            <a href="#how-it-works" className="hover:text-[#6257F5] transition">How it works</a>
            <a href="#principles" className="hover:text-[#6257F5] transition">Safety & Principles</a>
            <a href="#features" className="hover:text-[#6257F5] transition">Features</a>
            <a href="#faq" className="hover:text-[#6257F5] transition">FAQ</a>
          </nav>

          <div className="flex items-center gap-3">
            <NavLink
              to="/login"
              className="text-sm font-semibold text-[#77758A] hover:text-[#292443] px-3.5 py-2 rounded-xl transition"
            >
              Sign in
            </NavLink>
            <NavLink
              to="/register"
              className="text-sm font-semibold text-white bg-[#6257F5] hover:bg-[#5148d4] px-4 py-2 rounded-xl shadow-sm shadow-violet-500/25 transition flex items-center gap-1.5"
            >
              <span>Get Started</span>
              <ArrowRight className="w-4 h-4" />
            </NavLink>
          </div>
        </div>
      </header>

      {/* ── Hero Section ──────────────────────────────────────────── */}
      <section className="pt-16 pb-20 px-6 max-w-7xl mx-auto w-full text-center">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#F0EEFF] text-[#6257F5] text-xs font-semibold mb-6 border border-[#6257F5]/20">
          <Sparkles className="w-3.5 h-3.5 text-[#22B8B0]" />
          <span>V1 Medical Document Intelligence</span>
        </div>

        <h1 className="text-4xl md:text-6xl font-extrabold tracking-tight text-[#292443] max-w-3xl mx-auto leading-tight">
          Upload a medical document once. <br />
          <span className="text-[#6257F5]">Understand it with confidence.</span>
        </h1>

        <p className="mt-6 text-lg md:text-xl text-[#77758A] max-w-2xl mx-auto leading-relaxed">
          JohnnySummUP extracts structured measurements, flags values outside the source report’s
          printed reference intervals, and produces plain-language explanations grounded in verifiable evidence.
        </p>

        <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-4">
          <NavLink
            to="/register"
            className="w-full sm:w-auto px-6 py-3.5 rounded-xl bg-[#6257F5] hover:bg-[#5148d4] text-white font-semibold text-base shadow-lg shadow-violet-500/25 transition flex items-center justify-center gap-2"
          >
            <span>Open Medical Workspace</span>
            <ArrowRight className="w-4 h-4" />
          </NavLink>
          <a
            href="#how-it-works"
            className="w-full sm:w-auto px-6 py-3.5 rounded-xl bg-white hover:bg-slate-50 text-[#292443] border border-[#E8E7F0] font-semibold text-base transition flex items-center justify-center gap-2"
          >
            <span>Explore How it Works</span>
          </a>
        </div>

        {/* Product Workflow Preview Card */}
        <div className="mt-14 max-w-4xl mx-auto bg-white rounded-2xl border border-[#E8E7F0] shadow-xl shadow-slate-200/50 p-6 md:p-8 text-left">
          <div className="flex items-center justify-between pb-4 border-b border-[#E8E7F0] mb-6">
            <div className="flex items-center gap-2 text-xs font-semibold text-[#77758A]">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span>
              Live Pipeline Demonstration: Blood Test Report
            </div>
            <span className="text-xs font-medium text-[#6257F5] bg-[#F0EEFF] px-2.5 py-0.5 rounded-full">
              Deterministic Grounding
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-start">
            {/* Left: Extracted Measurement */}
            <div className="bg-[#F7F7FB] p-5 rounded-xl border border-[#E8E7F0] space-y-3">
              <div className="text-xs font-bold uppercase text-[#77758A] tracking-wider">
                1. Extracted Measurement
              </div>
              <div className="flex items-baseline justify-between">
                <div>
                  <h3 className="font-bold text-lg text-[#292443]">Hemoglobin</h3>
                  <p className="text-xs text-[#77758A]">Page 1 • Snippet: &quot;Hemoglobin 12.4 g/dL&quot;</p>
                </div>
                <div className="text-right">
                  <div className="text-2xl font-black text-[#292443]">12.4 <span className="text-sm font-normal text-[#77758A]">g/dL</span></div>
                  <span className="text-xs text-[#B98512] font-semibold">Ref: 13.0 - 17.0</span>
                </div>
              </div>
              <div className="pt-2 flex items-center gap-2">
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-[#fdf6e3] text-[#B98512]">
                  Below report interval
                </span>
                <span className="text-xs text-[#77758A]">Source Lab Flag: LOW</span>
              </div>
            </div>

            {/* Right: Plain-Language Grounded Explanation */}
            <div className="bg-[#F7F7FB] p-5 rounded-xl border border-[#E8E7F0] space-y-3">
              <div className="text-xs font-bold uppercase text-[#77758A] tracking-wider flex items-center justify-between">
                <span>2. Evidence-Grounded Explanation</span>
                <span className="text-[11px] font-normal text-emerald-600">✓ 100% Traceable</span>
              </div>
              <p className="text-xs text-[#292443] leading-relaxed">
                The extracted hemoglobin level is <b>12.4 g/dL</b>, which is below the reference range of <b>13.0 - 17.0 g/dL</b> printed directly on your laboratory report.
              </p>
              <div className="p-2.5 rounded-lg bg-white border border-[#E8E7F0] text-xs text-[#77758A]">
                <span className="font-semibold text-[#6257F5]">Suggested discussion with your doctor:</span>
                <p className="mt-0.5">What factors might be contributing to this hemoglobin reading?</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Core Principles ───────────────────────────────────────── */}
      <section id="principles" className="py-16 bg-white border-y border-[#E8E7F0] px-6">
        <div className="max-w-7xl mx-auto">
          <div className="text-center max-w-2xl mx-auto mb-12">
            <h2 className="text-2xl md:text-3xl font-bold text-[#292443]">Non-negotiable Medical Principles</h2>
            <p className="mt-3 text-sm text-[#77758A]">
              We designed JohnnySummUP with strict medical safety boundaries and zero guesswork.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="p-6 rounded-2xl bg-[#F7F7FB] border border-[#E8E7F0]">
              <div className="w-10 h-10 rounded-xl bg-violet-100 text-[#6257F5] flex items-center justify-center font-bold mb-4">
                <FileCheck className="w-5 h-5" />
              </div>
              <h3 className="font-bold text-base text-[#292443]">Original File is Source of Truth</h3>
              <p className="mt-2 text-xs text-[#77758A] leading-relaxed">
                AI extraction never replaces your original document. The uploaded file is preserved intact and can be previewed side-by-side with findings.
              </p>
            </div>

            <div className="p-6 rounded-2xl bg-[#F7F7FB] border border-[#E8E7F0]">
              <div className="w-10 h-10 rounded-xl bg-teal-100 text-[#22B8B0] flex items-center justify-center font-bold mb-4">
                <ShieldCheck className="w-5 h-5" />
              </div>
              <h3 className="font-bold text-base text-[#292443]">Deterministic Range Logic</h3>
              <p className="mt-2 text-xs text-[#77758A] leading-relaxed">
                We never ask an AI model to guess if a value is normal. Results are checked using deterministic code strictly against the range printed on that specific report.
              </p>
            </div>

            <div className="p-6 rounded-2xl bg-[#F7F7FB] border border-[#E8E7F0]">
              <div className="w-10 h-10 rounded-xl bg-amber-100 text-[#B98512] flex items-center justify-center font-bold mb-4">
                <Lock className="w-5 h-5" />
              </div>
              <h3 className="font-bold text-base text-[#292443]">No Diagnosing or Prescribing</h3>
              <p className="mt-2 text-xs text-[#77758A] leading-relaxed">
                JohnnySummUP is purely informational. It does not infer diseases, prescribe treatments, or recommend medication alterations.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ── How It Works ─────────────────────────────────────────── */}
      <section id="how-it-works" className="py-20 px-6 max-w-7xl mx-auto w-full">
        <div className="text-center max-w-2xl mx-auto mb-14">
          <span className="text-xs font-semibold text-[#6257F5] uppercase tracking-wider">Five-Stage Pipeline</span>
          <h2 className="mt-2 text-3xl font-extrabold text-[#292443]">From PDF to Structured Understanding</h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          {[
            { step: '01', title: 'File Validation', desc: 'Secure signature, size, and integrity check.' },
            { step: '02', title: 'Text Acquisition', desc: 'Digital PDF extraction with OCR fallback.' },
            { step: '03', title: 'Field Extraction', desc: 'Test names, values, units, and intervals extracted.' },
            { step: '04', title: 'Deterministic Rules', desc: 'Arithmetic checks against report bounds.' },
            { step: '05', title: 'Grounded Summary', desc: 'Plain-language review with evidence links.' },
          ].map((item, idx) => (
            <div key={idx} className="bg-white p-5 rounded-2xl border border-[#E8E7F0] relative">
              <span className="text-2xl font-black text-[#6257F5]/20 block mb-2">{item.step}</span>
              <h3 className="font-bold text-sm text-[#292443]">{item.title}</h3>
              <p className="mt-1 text-xs text-[#77758A]">{item.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── FAQ ───────────────────────────────────────────────────── */}
      <section id="faq" className="py-16 bg-white border-t border-[#E8E7F0] px-6">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-2xl md:text-3xl font-bold text-[#292443]">Frequently Asked Questions</h2>
          </div>

          <div className="space-y-4">
            {[
              {
                q: 'What file formats are supported?',
                a: 'JohnnySummUP V1 accepts digital PDFs, scanned PDFs, and common image formats (PNG, JPEG, WebP) up to 20MB.',
              },
              {
                q: 'How does JohnnySummUP know if a value is high or low?',
                a: 'We evaluate results exclusively against the reference interval printed on your specific laboratory report. Laboratories use different testing methodologies and equipment, so universal normal ranges are never assumed.',
              },
              {
                q: 'Is my medical data kept private?',
                a: 'Yes. Files and extracted data are strictly scoped to your authenticated account and are never used to train third-party public models.',
              },
              {
                q: 'Can JohnnySummUP give me a diagnosis?',
                a: 'No. JohnnySummUP is strictly an informational tool designed to help you prepare questions and review data alongside qualified healthcare professionals.',
              },
            ].map((faq, idx) => (
              <div key={idx} className="p-5 rounded-xl border border-[#E8E7F0] bg-[#F7F7FB]">
                <h3 className="font-semibold text-sm text-[#292443] flex items-center gap-2">
                  <HelpCircle className="w-4 h-4 text-[#6257F5]" />
                  <span>{faq.q}</span>
                </h3>
                <p className="mt-2 text-xs text-[#77758A] leading-relaxed pl-6">{faq.a}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Footer ────────────────────────────────────────────────── */}
      <footer className="mt-auto bg-white border-t border-[#E8E7F0] py-8 px-6 text-center text-xs text-[#77758A]">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <MascotBadge size="sm" />
          <p>© 2026 JohnnySummUP — V1 Medical Intelligence. All rights reserved.</p>
          <div className="flex items-center gap-6">
            <a href="#principles" className="hover:text-[#6257F5]">Safety Guidelines</a>
            <NavLink to="/login" className="hover:text-[#6257F5]">Sign in</NavLink>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;

