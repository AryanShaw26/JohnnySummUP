import React, { useState } from 'react';
import {
  User as UserIcon,
  Shield,
  Trash2,
  Download,
  CheckCircle2,
  AlertTriangle,
  Globe,
  Lock,
} from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import api from '../services/api';

export const SettingsPage: React.FC = () => {
  const { user, refreshUser } = useAuth();
  const [fullName, setFullName] = useState(user?.fullName || '');
  const [unitSystem, setUnitSystem] = useState('metric');
  const [savedSuccess, setSavedSuccess] = useState(false);
  const [isUpdating, setIsUpdating] = useState(false);

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsUpdating(true);
    try {
      await api.updateProfile({ fullName });
      await refreshUser();
      setSavedSuccess(true);
      setTimeout(() => setSavedSuccess(false), 3000);
    } catch (err) {
      alert('Failed to update profile.');
    } finally {
      setIsUpdating(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-8">
      {/* ── Page Header ───────────────────────────────────────────── */}
      <div>
        <h1 className="text-2xl font-extrabold tracking-tight text-[#292443]">
          Account & Privacy Settings
        </h1>
        <p className="mt-1 text-xs text-[#77758A]">
          Manage your personal profile, unit preferences, and privacy controls.
        </p>
      </div>

      {savedSuccess && (
        <div className="p-3.5 rounded-xl bg-[#e8f5ee] border border-emerald-200 text-xs text-[#168A4A] flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          <span>Profile changes saved successfully.</span>
        </div>
      )}

      {/* ── Profile Section ───────────────────────────────────────── */}
      <div className="bg-white p-6 rounded-2xl border border-[#E8E7F0] shadow-sm space-y-5">
        <h2 className="text-sm font-bold text-[#292443] flex items-center gap-2">
          <UserIcon className="w-4 h-4 text-[#6257F5]" />
          <span>Profile Details</span>
        </h2>

        <form onSubmit={handleSaveProfile} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-[#292443] mb-1.5">
                Full Name
              </label>
              <input
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl border border-[#E8E7F0] text-xs focus:border-[#6257F5] bg-white font-medium"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-[#292443] mb-1.5">
                Email Address
              </label>
              <input
                type="email"
                disabled
                value={user?.email || ''}
                className="w-full px-3.5 py-2.5 rounded-xl border border-[#E8E7F0] text-xs bg-slate-50 text-slate-500 cursor-not-allowed"
              />
            </div>
          </div>

          <div className="pt-2">
            <button
              type="submit"
              disabled={isUpdating}
              className="px-4 py-2 rounded-xl bg-[#6257F5] hover:bg-[#5148d4] text-white text-xs font-semibold shadow-sm transition disabled:opacity-50"
            >
              {isUpdating ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </form>
      </div>

      {/* ── Preferences Section ───────────────────────────────────── */}
      <div className="bg-white p-6 rounded-2xl border border-[#E8E7F0] shadow-sm space-y-4">
        <h2 className="text-sm font-bold text-[#292443] flex items-center gap-2">
          <Globe className="w-4 h-4 text-[#22B8B0]" />
          <span>Medical Units & Display</span>
        </h2>

        <div className="space-y-2 text-xs">
          <label className="block font-semibold text-[#292443]">
            Preferred Unit System
          </label>
          <div className="flex items-center gap-3">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                name="units"
                value="metric"
                checked={unitSystem === 'metric'}
                onChange={() => setUnitSystem('metric')}
                className="text-[#6257F5] focus:ring-[#6257F5]"
              />
              <span>Standard Metric (g/dL, mg/dL, mmol/L)</span>
            </label>
          </div>
          <p className="text-[11px] text-[#77758A]">
            * Note: JohnnySummUP always preserves the original units printed on your source laboratory report.
          </p>
        </div>
      </div>

      {/* ── Privacy & Data Retention Notice ───────────────────────── */}
      <div className="bg-white p-6 rounded-2xl border border-[#E8E7F0] shadow-sm space-y-4">
        <h2 className="text-sm font-bold text-[#292443] flex items-center gap-2">
          <Shield className="w-4 h-4 text-[#6257F5]" />
          <span>Privacy & Data Protection</span>
        </h2>

        <div className="text-xs text-[#77758A] space-y-2 leading-relaxed">
          <p>
            • Your uploaded medical reports and extracted data are encrypted at rest and in transit.
          </p>
          <p>
            • Document processing runs on private server-side workers and is strictly tenant-scoped to your account.
          </p>
          <p>
            • We do NOT use your private medical documents to train generic public models.
          </p>
        </div>

        <div className="pt-4 border-t border-[#E8E7F0] flex flex-col sm:flex-row items-center justify-between gap-3">
          <button
            type="button"
            onClick={() => alert('Data export job initiated. You will receive a notification when ready.')}
            className="inline-flex items-center gap-2 text-xs font-semibold text-[#6257F5] bg-[#F0EEFF] px-3.5 py-2 rounded-xl border border-[#6257F5]/20 hover:bg-[#F0EEFF]/80 transition"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Export Account Data</span>
          </button>

          <button
            type="button"
            onClick={() => alert('Account deletion requires contacting support to protect medical records.')}
            className="inline-flex items-center gap-1.5 text-xs text-[#C93636] hover:underline"
          >
            <Trash2 className="w-3.5 h-3.5" />
            <span>Request Account Deletion</span>
          </button>
        </div>
      </div>
    </div>
  );
};

export default SettingsPage;

