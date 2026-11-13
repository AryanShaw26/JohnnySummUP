import { ArrowUpRight, BookOpenText, BriefcaseBusiness, GraduationCap, HeartPulse, Landmark, Shield } from "lucide-react";
import { Link } from "react-router-dom";
import { BrandLogo } from "../components/common/BrandLogo";
import { useAuth } from "../hooks/useAuth";

const areas = [
  { title: "Medical", summary: "Health information", path: "/app/medical", icon: HeartPulse },
  { title: "Legal", summary: "Documents & agreements", path: "/app/legal", icon: BookOpenText },
  { title: "Finance", summary: "Financial details", path: "/app/finance", icon: Landmark },
  { title: "Insurance", summary: "Policies & coverage", path: "/app/insurance", icon: Shield },
  { title: "Education", summary: "Learning & school", path: "/app/education", icon: GraduationCap },
  { title: "Employment & Government", summary: "Work & public services", path: "/app/employment-government", icon: BriefcaseBusiness },
];

export function OverviewPage() {
  const { user } = useAuth();
  return (
    <div className="overview-page">
      <section className="welcome-card">
        <div className="welcome-card__copy">
          <p className="eyebrow">YOUR WORKSPACE</p>
          <h2>Welcome, {user?.full_name.split(" ")[0]}.</h2>
          <p>This is your starting point for a more approachable way to work with important information.</p>
          <span className="welcome-card__status"><span /> Your workspace is ready</span>
        </div>
        <div className="welcome-card__brand"><BrandLogo compact /></div>
      </section>
      <div className="content-heading">
        <div><p className="eyebrow">EXPLORE YOUR WORKSPACE</p><h2>Choose an area to explore</h2></div>
        <span className="content-heading__note">Workspaces ready</span>
      </div>
      <div className="workspace-grid">
        {areas.map(({ title, summary, path, icon: Icon }, index) => (
          <Link className="workspace-card" to={path} key={path}>
            <span className={`workspace-card__icon workspace-card__icon--${index + 1}`}><Icon size={21} aria-hidden="true" /></span>
            <ArrowUpRight className="workspace-card__arrow" size={18} aria-hidden="true" />
            <h3>{title}</h3>
            <p>{summary}</p>
            <span className="workspace-card__label">Open workspace</span>
          </Link>
        ))}
      </div>
      <section className="next-step">
        <span className="next-step__mark">✦</span>
        <div><h3>Good things take thoughtful steps.</h3><p>We’re laying the foundation for helpful tools. For now, explore the workspace or visit your settings.</p></div>
        <Link to="/app/settings" className="text-link">View settings <ArrowUpRight size={16} aria-hidden="true" /></Link>
      </section>
    </div>
  );
}
