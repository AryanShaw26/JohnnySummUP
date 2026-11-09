import {
  Activity,
  BrainCircuit,
  Clock,
  FileText,
  LayoutDashboard,
} from "lucide-react";
import { Link, useLocation } from "react-router-dom";

export function MedicalNavigation() {
  const location = useLocation();
  const path = location.pathname;

  // Identify active group
  let activeGroup = "overview";
  if (path.startsWith("/app/medical/documents")) {
    activeGroup = "documents";
  } else if (path.startsWith("/app/medical/analysis")) {
    activeGroup = "analysis";
  } else if (path.startsWith("/app/medical/analytics")) {
    activeGroup = "analytics";
  } else if (path.startsWith("/app/medical/history")) {
    activeGroup = "history";
  }

  const groups = [
    { id: "overview", label: "Overview", icon: LayoutDashboard, path: "/app/medical" },
    { id: "documents", label: "Documents", icon: FileText, path: "/app/medical/documents" },
    { id: "analysis", label: "AI Analysis", icon: BrainCircuit, path: "/app/medical/analysis/summaries" },
    { id: "analytics", label: "Health Analytics", icon: Activity, path: "/app/medical/analytics/trends" },
    { id: "history", label: "History", icon: Clock, path: "/app/medical/history/uploads" },
  ];

  // Subnav pills for each group
  const subnavs: Record<string, Array<{ label: string; path: string }>> = {
    overview: [
      { label: "Medical Dashboard", path: "/app/medical" },
      { label: "Recent Reports", path: "/app/medical/documents" },
      { label: "Important Findings", path: "/app/medical/analysis/flags" },
    ],
    documents: [
      { label: "Upload Report", path: "/app/medical/documents/upload" },
      { label: "All Reports", path: "/app/medical/documents" },
      { label: "Prescriptions", path: "/app/medical/documents/prescriptions" },
      { label: "Laboratory Reports", path: "/app/medical/documents/laboratory" },
    ],
    analysis: [
      { label: "Report Summaries", path: "/app/medical/analysis/summaries" },
      { label: "Extracted Findings", path: "/app/medical/analysis/findings" },
      { label: "Abnormality Flags", path: "/app/medical/analysis/flags" },
    ],
    analytics: [
      { label: "Health Trends", path: "/app/medical/analytics/trends" },
      { label: "Parameter Comparison", path: "/app/medical/analytics/comparison" },
      { label: "Historical Analytics", path: "/app/medical/analytics/history" },
    ],
    history: [
      { label: "Previous Uploads", path: "/app/medical/history/uploads" },
      { label: "Previous Summaries", path: "/app/medical/history/summaries" },
      { label: "Report Timeline", path: "/app/medical/history/timeline" },
    ],
  };

  const currentSubnav = subnavs[activeGroup] || [];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      {/* Primary Groups Bar */}
      <nav className="medical-nav" aria-label="Medical workspace sections">
        <div className="medical-nav__groups">
          {groups.map(({ id, label, icon: Icon, path: groupPath }) => {
            const isActive = activeGroup === id;
            return (
              <Link
                key={id}
                to={groupPath}
                className={`medical-nav__item ${isActive ? "medical-nav__item--active" : ""}`}
              >
                <Icon size={16} aria-hidden="true" />
                <span>{label}</span>
              </Link>
            );
          })}
        </div>
      </nav>

      {/* Sub-navigation Pills */}
      {currentSubnav.length > 0 && (
        <div className="medical-subnav" aria-label="Medical sub-pages">
          {currentSubnav.map((item) => {
            const isSubActive =
              path === item.path ||
              (item.path === "/app/medical" && path === "/app/medical/");
            return (
              <Link
                key={item.label}
                to={item.path}
                className={`medical-subnav__pill ${
                  isSubActive ? "medical-subnav__pill--active" : ""
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
