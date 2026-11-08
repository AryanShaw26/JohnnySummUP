import { Outlet, useLocation } from "react-router-dom";
import { MedicalNavigation } from "../../components/medical/MedicalNavigation";
import { MedicalOverviewPage } from "./MedicalOverview";

export function MedicalWorkspace() {
  const location = useLocation();
  const isOverview =
    location.pathname === "/app/medical" || location.pathname === "/app/medical/";

  return (
    <div className="medical-workspace">
      {/* Secondary Horizontal Navigation */}
      <MedicalNavigation />

      {/* Main Content Area */}
      {isOverview ? <MedicalOverviewPage /> : <Outlet />}
    </div>
  );
}
