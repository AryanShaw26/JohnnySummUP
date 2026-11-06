import {
  ArrowRight,
  BookOpenText,
  BriefcaseBusiness,
  GraduationCap,
  HeartPulse,
  Landmark,
  Shield,
} from "lucide-react";
import { Link } from "react-router-dom";
import { BrandLogo } from "../components/common/BrandLogo";

const domains = [
  { title: "Medical", detail: "Health information, made easier to navigate.", icon: HeartPulse },
  { title: "Legal", detail: "A clearer starting point for complex paperwork.", icon: BookOpenText },
  { title: "Finance", detail: "Make sense of the details that shape decisions.", icon: Landmark },
  { title: "Insurance", detail: "Find your way through policy information.", icon: Shield },
  { title: "Education", detail: "Bring clarity to learning and school documents.", icon: GraduationCap },
  { title: "Employment & Government", detail: "Understand the paperwork behind next steps.", icon: BriefcaseBusiness },
];

export function LandingPage() {
  return (
    <div className="landing">
      <header className="landing-header">
        <Link to="/" aria-label="JohnnySummUP home"><BrandLogo /></Link>
        <nav className="landing-header__nav" aria-label="Account navigation">
          <Link className="button button--quiet" to="/login">Log in</Link>
          <Link className="button button--primary button--compact" to="/register">
            Get started <ArrowRight size={16} aria-hidden="true" />
          </Link>
        </nav>
      </header>

      <main>
        <section className="hero page-width">
          <div className="hero__copy">
            <span className="pill"><span className="pill__dot" /> A clearer way to begin</span>
            <h1>Important documents.<br /><span>Less overwhelming.</span></h1>
            <p className="hero__intro">
              Meet a more approachable home for the information that matters. JohnnySummUP is building toward clearer document experiences, one step at a time.
            </p>
            <div className="hero__actions">
              <Link className="button button--primary button--large" to="/register">
                Create your account <ArrowRight size={18} aria-hidden="true" />
              </Link>
              <Link className="text-link" to="/login">Already have an account? Log in</Link>
            </div>
            <div className="hero__note"><span aria-hidden="true">✦</span> A brave companion for life’s fine print.</div>
          </div>
          <div className="hero-art" aria-label="JohnnySummUP brand">
            <div className="hero-art__halo" />
            <div className="hero-art__card hero-art__card--top"><HeartPulse size={17} /><span>Health notes</span><i /></div>
            <div className="hero-art__brand"><BrandLogo /></div>
            <div className="hero-art__card hero-art__card--bottom"><BookOpenText size={17} /><span>Everyday paperwork</span><i /></div>
            <div className="hero-art__spark hero-art__spark--one">✦</div>
            <div className="hero-art__spark hero-art__spark--two">✧</div>
          </div>
        </section>

        <section className="domains-section page-width">
          <div className="section-heading">
            <p className="eyebrow">A PLACE FOR WHAT MATTERS</p>
            <h2>One thoughtful starting point.</h2>
            <p>Explore the areas JohnnySummUP is being designed to support. These are just the beginning.</p>
          </div>
          <div className="domain-grid">
            {domains.map(({ title, detail, icon: Icon }, index) => (
              <article className="domain-card" key={title}>
                <span className={`domain-card__icon domain-card__icon--${index + 1}`}><Icon size={20} aria-hidden="true" /></span>
                <h3>{title}</h3>
                <p>{detail}</p>
                <span className="domain-card__soon">Coming in future phases</span>
              </article>
            ))}
          </div>
        </section>

        <section className="closing-cta">
          <div className="page-width closing-cta__inner">
            <div>
              <p className="eyebrow">YOUR BRAVE SUMMARIZER</p>
              <h2>Start with a little more clarity.</h2>
              <p>Create an account to see the JohnnySummUP workspace take shape.</p>
            </div>
            <Link className="button button--light button--large" to="/register">Get started <ArrowRight size={18} aria-hidden="true" /></Link>
          </div>
        </section>
      </main>
      <footer className="landing-footer page-width">
        <BrandLogo compact />
        <span>© {new Date().getFullYear()} JohnnySummUP</span>
        <span>Built for a clearer next step.</span>
      </footer>
    </div>
  );
}
