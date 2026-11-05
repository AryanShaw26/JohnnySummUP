import React, { useState } from 'react';
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  UploadCloud,
  FolderOpen,
  LineChart,
  Pill,
  Sparkles,
  GitCompare,
  Settings,
  LogOut,
  Menu,
  X,
  FileText,
  ShieldCheck,
  ChevronRight,
  ExternalLink,
} from 'lucide-react';
import { useAuth } from '../../hooks/useAuth';
import MascotBadge from '../common/MascotBadge';

export const AppLayout: React.FC = () => {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navItems = [
    { name: 'Overview', path: '/app/overview', icon: LayoutDashboard },
    { name: 'Upload Report', path: '/app/upload', icon: UploadCloud, highlight: true },
    { name: 'My Records', path: '/app/records', icon: FolderOpen },
    { name: 'Health Analytics', path: '/app/analytics', icon: LineChart },
    { name: 'Prescriptions', path: '/app/prescriptions', icon: Pill },
    { name: 'AI Insights', path: '/app/insights', icon: Sparkles },
    { name: 'Compare Reports', path: '/app/compare', icon: GitCompare },
  ];

  const currentNav = navItems.find((item) => location.pathname.startsWith(item.path)) || {
    name: location.pathname.includes('/records/') ? 'Record Detail' : 'Medical Workspace',
  };

  return (
    <div className="min-h-screen bg-[#F7F7FB] flex flex-col md:flex-row text-[#292443]">
      {/* ── Left Sidebar (Desktop) ────────────────────────────────── */}
      <aside className="hidden md:flex flex-col w-64 border-r border-[#E8E7F0] bg-white sticky top-0 h-screen select-none shrink-0 z-20">
        {/* Brand & Workspace Label */}
        <div className="p-5 border-b border-[#E8E7F0]">
          <MascotBadge size="sm" />
          <div className="mt-3 flex items-center justify-between">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-[#F0EEFF] text-[#6257F5] border border-[#6257F5]/20">
              <span className="w-1.5 h-1.5 rounded-full bg-[#6257F5]"></span>
              Medical Workspace
            </span>
            <span className="text-[11px] text-[#77758A] font-medium">V1 Baseline</span>
          </div>
        </div>

        {/* Navigation Links */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname.startsWith(item.path);
            return (
              <NavLink
                key={item.path}
                to={item.path}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all ${
                  isActive
                    ? 'bg-[#F0EEFF] text-[#6257F5] font-semibold'
                    : 'text-[#77758A] hover:text-[#292443] hover:bg-slate-50'
                } ${item.highlight && !isActive ? 'border border-[#6257F5]/30 bg-violet-50/40 text-[#6257F5]' : ''}`}
              >
                <Icon
                  className={`w-4 h-4 shrink-0 ${
                    isActive ? 'text-[#6257F5]' : item.highlight ? 'text-[#6257F5]' : 'text-[#77758A]'
                  }`}
                />
                <span>{item.name}</span>
                {item.highlight && !isActive && (
                  <span className="ml-auto text-[10px] font-semibold bg-[#6257F5] text-white px-1.5 py-0.5 rounded-full">
                    New
                  </span>
                )}
              </NavLink>
            );
          })}
        </nav>

        {/* Safety Disclaimer Callout */}
        <div className="p-3 mx-3 mb-2 rounded-xl bg-slate-50 border border-[#E8E7F0] text-[11px] text-[#77758A] leading-relaxed">
          <div className="flex items-center gap-1 text-[#292443] font-semibold mb-1">
            <ShieldCheck className="w-3.5 h-3.5 text-[#22B8B0]" />
            <span>Informational Support</span>
          </div>
          Evidence-grounded summaries only. Consult qualified healthcare professionals for diagnosis.
        </div>

        {/* User Profile & Footer Controls */}
        <div className="p-3 border-t border-[#E8E7F0] bg-white">
          <div className="flex items-center justify-between p-2 rounded-xl hover:bg-slate-50 transition">
            <div className="flex items-center gap-2.5 overflow-hidden">
              <div className="w-8 h-8 rounded-full bg-[#6257F5]/10 text-[#6257F5] font-bold flex items-center justify-center text-xs shrink-0">
                {user?.fullName?.charAt(0) || user?.email?.charAt(0).toUpperCase() || 'U'}
              </div>
              <div className="truncate">
                <p className="text-xs font-semibold text-[#292443] truncate">{user?.fullName || 'User'}</p>
                <p className="text-[11px] text-[#77758A] truncate">{user?.email}</p>
              </div>
            </div>
            <div className="flex items-center gap-1">
              <NavLink
                to="/app/settings"
                title="Settings"
                className="p-1.5 text-[#77758A] hover:text-[#6257F5] hover:bg-slate-100 rounded-lg transition"
              >
                <Settings className="w-4 h-4" />
              </NavLink>
              <button
                onClick={logout}
                title="Sign out"
                className="p-1.5 text-[#77758A] hover:text-[#C93636] hover:bg-red-50 rounded-lg transition"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </aside>

      {/* ── Mobile Header ─────────────────────────────────────────── */}
      <header className="md:hidden flex items-center justify-between px-4 py-3 bg-white border-b border-[#E8E7F0] sticky top-0 z-30">
        <MascotBadge size="sm" />
        <button
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          className="p-2 text-[#77758A] hover:text-[#292443] rounded-lg border border-[#E8E7F0]"
        >
          {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </header>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <div className="md:hidden fixed inset-0 top-[57px] bg-white z-40 p-4 space-y-2 overflow-y-auto">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname.startsWith(item.path);
            return (
              <NavLink
                key={item.path}
                to={item.path}
                onClick={() => setMobileMenuOpen(false)}
                className={`flex items-center gap-3 px-4 py-3 rounded-xl text-base font-medium ${
                  isActive ? 'bg-[#F0EEFF] text-[#6257F5] font-semibold' : 'text-[#77758A]'
                }`}
              >
                <Icon className="w-5 h-5" />
                <span>{item.name}</span>
              </NavLink>
            );
          })}
          <div className="pt-4 border-t border-[#E8E7F0] flex items-center justify-between">
            <NavLink
              to="/app/settings"
              onClick={() => setMobileMenuOpen(false)}
              className="flex items-center gap-2 text-sm text-[#77758A]"
            >
              <Settings className="w-4 h-4" />
              <span>Settings</span>
            </NavLink>
            <button
              onClick={() => {
                setMobileMenuOpen(false);
                logout();
              }}
              className="flex items-center gap-2 text-sm text-[#C93636]"
            >
              <LogOut className="w-4 h-4" />
              <span>Log out</span>
            </button>
          </div>
        </div>
      )}

      {/* ── Main Canvas Content Area ──────────────────────────────── */}
      <main className="flex-1 flex flex-col min-w-0 h-screen overflow-y-auto">
        {/* Top Bar with Breadcrumbs & Action */}
        <div className="bg-white border-b border-[#E8E7F0] px-6 py-3.5 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-2 text-xs text-[#77758A]">
            <NavLink to="/app/overview" className="hover:text-[#6257F5]">
              Medical
            </NavLink>
            <ChevronRight className="w-3.5 h-3.5" />
            <span className="font-semibold text-[#292443]">{currentNav.name}</span>
          </div>

          <div className="flex items-center gap-3">
            <NavLink
              to="/app/upload"
              className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-xl bg-[#6257F5] hover:bg-[#5148d4] text-white text-xs font-semibold shadow-sm shadow-violet-500/20 transition"
            >
              <UploadCloud className="w-3.5 h-3.5" />
              <span>Upload Report</span>
            </NavLink>
          </div>
        </div>

        {/* Content Viewport */}
        <div className="flex-1 p-6 md:p-8 max-w-7xl w-full mx-auto">
          <Outlet />
        </div>
      </main>
    </div>
  );
};

export default AppLayout;

