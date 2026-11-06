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
              <Route path=":domain" element={<DomainPage />} />
            </Route>
          </Route>
          <Route path="*" element={<NotFound />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
