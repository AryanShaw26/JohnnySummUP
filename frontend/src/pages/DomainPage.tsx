import { ArrowLeft, Sparkles } from "lucide-react";
import { Link, useParams } from "react-router-dom";

const labels: Record<string, string> = {
  medical: "Medical",
  legal: "Legal",
  finance: "Finance",
  insurance: "Insurance",
  education: "Education",
  "employment-government": "Employment & Government",
};

export function DomainPage() {
  const { domain } = useParams();
  const title = domain ? labels[domain] : undefined;
  if (!title) {
    return <section className="placeholder-card"><h2>Area not found</h2><Link to="/app" className="text-link">Back to overview</Link></section>;
  }
  return (
    <section className="domain-placeholder">
      <Link to="/app" className="back-link"><ArrowLeft size={16} aria-hidden="true" /> Back to overview</Link>
      <div className="domain-placeholder__icon"><Sparkles size={22} aria-hidden="true" /></div>
      <p className="eyebrow">A NEW CHAPTER IS TAKING SHAPE</p>
      <h2>{title}</h2>
      <p className="domain-placeholder__copy">This part of JohnnySummUP is still in the works. Your workspace is ready, and helpful tools for this area will arrive in a future phase.</p>
      <span className="pill pill--muted">Coming in a future phase</span>
    </section>
  );
}
