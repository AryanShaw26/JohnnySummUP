import React, { useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { AlertCircle } from "lucide-react";
import { getWorkspaceConfig } from "./WorkspaceConfig";
import { WorkspaceOverview } from "./WorkspaceOverview";
import { WorkspaceDocumentsList } from "./WorkspaceDocumentsList";
import { WorkspaceUpload } from "./WorkspaceUpload";
import { WorkspaceFindings } from "./WorkspaceFindings";
import { WorkspaceChecklist } from "./WorkspaceChecklist";
import { WorkspaceCompare } from "./WorkspaceCompare";
import { WorkspaceDocumentDetail } from "./WorkspaceDocumentDetail";

interface WorkspaceHubProps {
  workspaceSlug?: string;
}

type TabType = "overview" | "documents" | "upload" | "findings" | "checklist" | "compare";

export const WorkspaceHub: React.FC<WorkspaceHubProps> = ({ workspaceSlug: propSlug }) => {
  const { domain } = useParams<{ domain?: string }>();
  const [searchParams, setSearchParams] = useSearchParams();

  // Resolve slug from prop or URL param
  const activeSlug = (propSlug || domain || "legal").toLowerCase();
  const config = getWorkspaceConfig(activeSlug);
  const IconComponent = config.icon;

  // Tab state (read from search query if present, otherwise default to overview)
  const initialTab = (searchParams.get("tab") as TabType) || "overview";
  const [activeTab, setActiveTab] = useState<TabType>(initialTab);

  // Selected document state
  const initialDocId = searchParams.get("docId");
  const [selectedDocId, setSelectedDocId] = useState<string | null>(initialDocId);

  const handleTabChange = (tab: TabType | string) => {
    const validTab = (tab as TabType) || "overview";
    setActiveTab(validTab);
    setSelectedDocId(null);
    setSearchParams({ tab: validTab });
  };

  const handleSelectDocument = (docId: string) => {
    setSelectedDocId(docId);
    setSearchParams({ tab: activeTab, docId });
  };

  const handleCloseDocumentDetail = () => {
    setSelectedDocId(null);
    setSearchParams({ tab: activeTab });
  };

  const handleUploadSuccess = (docId: string) => {
    setSelectedDocId(docId);
    setActiveTab("documents");
    setSearchParams({ tab: "documents", docId });
  };

  return (
    <div className="workspace-container">
      {/* Workspace Header Banner */}
      <div className="workspace-header">
        <div className="workspace-header-top">
          <div className="workspace-title-group">
            <span
              className="workspace-icon"
              style={{
                background: `${config.accentColor}15`,
                color: config.accentColor,
              }}
            >
              <IconComponent size={28} />
            </span>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                <h1 className="workspace-title">{config.name}</h1>
                <span
                  style={{
                    fontSize: "0.75rem",
                    fontWeight: 600,
                    textTransform: "uppercase",
                    padding: "2px 8px",
                    borderRadius: "12px",
                    background: `${config.accentColor}15`,
                    color: config.accentColor,
                  }}
                >
                  Workspace
                </span>
              </div>
              <p className="workspace-subtitle">{config.tagline}</p>
            </div>
          </div>

          <div style={{ display: "flex", gap: "0.5rem" }}>
            <button
              className={`workspace-btn ${activeTab === "upload" ? "workspace-btn-primary" : "workspace-btn-outline"}`}
              onClick={() => handleTabChange("upload")}
            >
              + Upload Document
            </button>
          </div>
        </div>

        {/* Disclaimer / Notice */}
        <div
          style={{
            marginTop: "1rem",
            padding: "0.6rem 0.9rem",
            background: "#f8fafc",
            border: "1px solid #e2e8f0",
            borderRadius: "6px",
            fontSize: "0.8rem",
            color: "#64748b",
            display: "flex",
            alignItems: "center",
            gap: "0.5rem",
          }}
        >
          <AlertCircle size={14} style={{ color: "#64748b", flexShrink: 0 }} />
          <span>
            JohnnySummUP extracts, compares, and synthesizes source documents for review purposes. Always verify findings against official executed copies.
          </span>
        </div>

        {/* Secondary Navigation Tabs */}
        <div className="workspace-nav-tabs">
          <button
            className={`workspace-tab-btn ${activeTab === "overview" && !selectedDocId ? "active" : ""}`}
            onClick={() => handleTabChange("overview")}
          >
            📊 Overview & Insights
          </button>
          <button
            className={`workspace-tab-btn ${activeTab === "documents" && !selectedDocId ? "active" : ""}`}
            onClick={() => handleTabChange("documents")}
          >
            📁 Documents Library
          </button>
          <button
            className={`workspace-tab-btn ${activeTab === "upload" ? "active" : ""}`}
            onClick={() => handleTabChange("upload")}
          >
            ⬆️ Upload & Analyze
          </button>
          <button
            className={`workspace-tab-btn ${activeTab === "findings" && !selectedDocId ? "active" : ""}`}
            onClick={() => handleTabChange("findings")}
          >
            ⚠️ Key Findings & Evidence
          </button>
          <button
            className={`workspace-tab-btn ${activeTab === "checklist" && !selectedDocId ? "active" : ""}`}
            onClick={() => handleTabChange("checklist")}
          >
            ✅ Action Checklist
          </button>
          <button
            className={`workspace-tab-btn ${activeTab === "compare" && !selectedDocId ? "active" : ""}`}
            onClick={() => handleTabChange("compare")}
          >
            ⚖️ Version Compare
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      {selectedDocId ? (
        <div>
          <WorkspaceDocumentDetail
            meta={config}
            documentId={selectedDocId}
            onBack={handleCloseDocumentDetail}
          />
        </div>
      ) : (
        <>
          {activeTab === "overview" && (
            <WorkspaceOverview
              meta={config}
              onNavigateTab={handleTabChange}
              onSelectDoc={handleSelectDocument}
            />
          )}

          {activeTab === "documents" && (
            <WorkspaceDocumentsList
              meta={config}
              onSelectDoc={handleSelectDocument}
              onUploadClick={() => handleTabChange("upload")}
            />
          )}

          {activeTab === "upload" && (
            <WorkspaceUpload
              meta={config}
              onUploadSuccess={handleUploadSuccess}
            />
          )}

          {activeTab === "findings" && (
            <WorkspaceFindings
              meta={config}
              onSelectDoc={handleSelectDocument}
            />
          )}

          {activeTab === "checklist" && (
            <WorkspaceChecklist
              meta={config}
              onSelectDoc={handleSelectDocument}
            />
          )}

          {activeTab === "compare" && (
            <WorkspaceCompare
              meta={config}
              onSelectDoc={handleSelectDocument}
            />
          )}
        </>
      )}
    </div>
  );
};
