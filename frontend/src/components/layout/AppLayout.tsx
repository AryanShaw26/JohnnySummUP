import {
  BookOpenText,
  BriefcaseBusiness,
  ChevronRight,
  GraduationCap,
  HeartPulse,
  Landmark,
  Menu,
  Settings,
  Shield,
  X,
} from "lucide-react";
import { useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { BrandLogo } from "../common/BrandLogo";
import { useAuth } from "../../hooks/useAuth";

const navigation = [
  { label: "Medical", path: "/app/medical", icon: HeartPulse },
  { label: "Legal", path: "/app/legal", icon: BookOpenText },
  { label: "Finance", path: "/app/finance", icon: Landmark },
  { label: "Insurance", path: "/app/insurance", icon: Shield },
  { label: "Education", path: "/app/education", icon: GraduationCap },
  { label: "Employment & Government", path: "/app/employment-government", icon: BriefcaseBusiness },
];

export function AppLayout() {
  const { user } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const location = useLocation();

  const currentLabel =
    location.pathname === "/app"
      ? "Overview"
      : location.pathname === "/app/settings"
        ? "Settings"
        : navigation.find((item) => item.path === location.pathname)?.label ?? "Overview";

  return (
    <div className="app-shell">
      {menuOpen && <button className="sidebar-backdrop" onClick={() => setMenuOpen(false)} aria-label="Close menu" />}
      <aside className={`sidebar ${menuOpen ? "sidebar--open" : ""}`}>
        <div className="sidebar__brand">
          <BrandLogo compact />
          <button className="icon-button sidebar__close" onClick={() => setMenuOpen(false)} aria-label="Close navigation">
            <X size={20} />
          </button>
        </div>
        <div className="sidebar__section-label">YOUR WORKSPACE</div>
        <nav className="sidebar__nav" aria-label="Main navigation">
          <NavLink to="/app" end onClick={() => setMenuOpen(false)} className={({ isActive }) => `nav-item ${isActive ? "nav-item--active" : ""}`}>
            <BookOpenText size={18} aria-hidden="true" />
            <span>Overview</span>
            <ChevronRight className="nav-item__chevron" size={15} aria-hidden="true" />
          </NavLink>
          {navigation.map(({ label, path, icon: Icon }) => (
            <NavLink key={path} to={path} onClick={() => setMenuOpen(false)} className={({ isActive }) => `nav-item ${isActive ? "nav-item--active" : ""}`}>
              <Icon size={18} aria-hidden="true" />
              <span>{label}</span>
              <ChevronRight className="nav-item__chevron" size={15} aria-hidden="true" />
            </NavLink>
          ))}
        </nav>
        <div className="sidebar__bottom">
          <NavLink to="/app/settings" onClick={() => setMenuOpen(false)} className={({ isActive }) => `nav-item ${isActive ? "nav-item--active" : ""}`}>
            <Settings size={18} aria-hidden="true" />
            <span>Settings</span>
            <ChevronRight className="nav-item__chevron" size={15} aria-hidden="true" />
          </NavLink>
          <div className="sidebar__profile">
            <div className="avatar" aria-hidden="true">{user?.full_name.slice(0, 1).toUpperCase()}</div>
            <div className="sidebar__identity">
              <strong>{user?.full_name}</strong>
              <span>{user?.email}</span>
            </div>
          </div>
        </div>
      </aside>
      <div className="app-main">
        <header className="app-header">
          <button className="icon-button app-header__menu" onClick={() => setMenuOpen(true)} aria-label="Open navigation">
            <Menu size={21} />
          </button>
          <div>
            <p className="eyebrow">JOHNNYSUMMUP</p>
            <h1>{currentLabel}</h1>
          </div>
          <div className="app-header__user">
            <span>{user?.full_name}</span>
            <div className="avatar avatar--small" aria-hidden="true">{user?.full_name.slice(0, 1).toUpperCase()}</div>
          </div>
        </header>
        <main className="app-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
