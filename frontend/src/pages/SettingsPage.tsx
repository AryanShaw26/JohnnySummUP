import { LogOut, Mail, ShieldCheck, UserRound } from "lucide-react";
import { useState } from "react";
import { useAuth } from "../hooks/useAuth";
import { ApiError } from "../services/api";

export function SettingsPage() {
  const { user, logout } = useAuth();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleLogout() {
    setSubmitting(true);
    setError(null);
    try {
      await logout();
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : "Unable to log out. Please try again.");
      setSubmitting(false);
    }
  }

  return (
    <div className="settings-page">
      <div className="content-heading"><div><p className="eyebrow">YOUR ACCOUNT</p><h2>Settings</h2><p>Manage your account details and sign-in session.</p></div></div>
      <section className="settings-card">
        <div className="settings-card__heading"><span className="settings-card__icon"><UserRound size={19} aria-hidden="true" /></span><div><h3>Profile data</h3><p>Your account information</p></div></div>
        <dl className="profile-details">
          <div><dt>Full name</dt><dd>{user?.full_name}</dd></div>
          <div><dt>Email address</dt><dd><Mail size={16} aria-hidden="true" />{user?.email}</dd></div>
        </dl>
      </section>
      <section className="settings-card settings-card--session">
        <div className="settings-card__heading"><span className="settings-card__icon settings-card__icon--green"><ShieldCheck size={19} aria-hidden="true" /></span><div><h3>Sign-in session</h3><p>Your account is protected with a secure sign-in session.</p></div></div>
        <div className="settings-card__action">
          <div><strong>Log out of JohnnySummUP</strong><span>You’ll need to log in again to access your workspace.</span></div>
          <button type="button" className="button button--outline-danger" onClick={handleLogout} disabled={submitting}><LogOut size={17} aria-hidden="true" />{submitting ? "Logging out…" : "Log out"}</button>
        </div>
        {error && <p className="form-alert" role="alert">{error}</p>}
      </section>
      <p className="settings-note">Profile editing and password recovery are not part of this initial release.</p>
    </div>
  );
}
