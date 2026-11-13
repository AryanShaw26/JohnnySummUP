import { BrowserRouter, Navigate, Outlet, Route, Routes } from "react-router-dom";
import type { ReactNode } from "react";
import { AuthError, AuthLoading, NotFound } from "./components/common/RouteStatus";
import { AppLayout } from "./components/layout/AppLayout";
import { AuthProvider, useAuth } from "./hooks/useAuth";
import { AuthPage } from "./pages/AuthPage";
import { DomainPage } from "./pages/DomainPage";
import { LandingPage } from "./pages/LandingPage";
import { OverviewPage } from "./pages/OverviewPage";
import { SettingsPage } from "./pages/SettingsPage";

import { PrescriptionsPage } from "./pages/medical/Prescriptions";
import { LaboratoryReportsPage } from "./pages/medical/LaboratoryReports";
import { MedicalWorkspace } from "./pages/medical/MedicalWorkspace";
import { MedicalOverviewPage } from "./pages/medical/MedicalOverview";
import { UploadReportPage } from "./pages/medical/UploadReport";
import { AllReportsPage } from "./pages/medical/AllReports";
import { ReportSummaryPage } from "./pages/medical/ReportSummary";
import { ExtractedFindingsPage } from "./pages/medical/ExtractedFindings";
import { AbnormalityFlagsPage } from "./pages/medical/AbnormalityFlags";
import { HealthTrendsPage } from "./pages/medical/HealthTrends";
import { ParameterComparisonPage } from "./pages/medical/ParameterComparison";
import { HistoricalAnalyticsPage } from "./pages/medical/HistoricalAnalytics";
import { PreviousUploadsPage } from "./pages/medical/PreviousUploads";
import { PreviousSummariesPage } from "./pages/medical/PreviousSummaries";
import { ReportTimelinePage } from "./pages/medical/ReportTimeline";

import { WorkspaceHub } from "./pages/workspace/WorkspaceHub";

function ProtectedRoutes() {
  const { status } = useAuth();
  if (status === "loading") return <AuthLoading />;
  if (status === "error") return <AuthError />;
  if (status === "unauthenticated") return <Navigate to="/login" replace />;
  return <Outlet />;
}

function PublicOnly({ children }: { children: ReactNode }) {
  const { status } = useAuth();
  if (status === "loading") return <AuthLoading />;
  if (status === "authenticated") return <Navigate to="/app" replace />;
  return children;
}

export default function App() {
  return (
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <AuthProvider>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<PublicOnly><AuthPage mode="login" /></PublicOnly>} />
          <Route path="/register" element={<PublicOnly><AuthPage mode="register" /></PublicOnly>} />
          <Route element={<ProtectedRoutes />}>
            <Route path="/app" element={<AppLayout />}>
              <Route index element={<OverviewPage />} />
              <Route path="settings" element={<SettingsPage />} />

              {/* Medical Workspace */}
              <Route path="medical" element={<MedicalWorkspace />}>
                <Route index element={<MedicalOverviewPage />} />

                {/* Documents */}
                <Route path="documents" element={<AllReportsPage />} />
                <Route path="documents/upload" element={<UploadReportPage />} />
                <Route path="documents/prescriptions" element={<PrescriptionsPage />} />
                <Route path="documents/laboratory" element={<LaboratoryReportsPage />} />
                <Route path="documents/:documentId" element={<ReportSummaryPage />} />

                {/* AI Analysis */}
                <Route path="analysis/summaries" element={<PreviousSummariesPage />} />
                <Route path="analysis/findings" element={<ExtractedFindingsPage />} />
                <Route path="analysis/flags" element={<AbnormalityFlagsPage />} />

                {/* Health Analytics */}
                <Route path="analytics/trends" element={<HealthTrendsPage />} />
                <Route path="analytics/comparison" element={<ParameterComparisonPage />} />
                <Route path="analytics/history" element={<HistoricalAnalyticsPage />} />

                {/* History */}
                <Route path="history/uploads" element={<PreviousUploadsPage />} />
                <Route path="history/summaries" element={<PreviousSummariesPage />} />
                <Route path="history/timeline" element={<ReportTimelinePage />} />
              </Route>

              {/* Five Non-Medical Workspaces */}
              <Route path="legal/*" element={<WorkspaceHub workspaceSlug="legal" />} />
              <Route path="finance/*" element={<WorkspaceHub workspaceSlug="finance" />} />
              <Route path="insurance/*" element={<WorkspaceHub workspaceSlug="insurance" />} />
              <Route path="education/*" element={<WorkspaceHub workspaceSlug="education" />} />
              <Route path="employment-government/*" element={<WorkspaceHub workspaceSlug="employment-government" />} />

              {/* Other domain placeholders */}
              <Route path=":domain" element={<DomainPage />} />
            </Route>
          </Route>
          <Route path="*" element={<NotFound />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
