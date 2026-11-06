import { RefreshCw } from "lucide-react";
import { Link } from "react-router-dom";
import { useAuth } from "../../hooks/useAuth";

export function AuthLoading() {
  return (
    <main className="route-status" aria-live="polite">
      <span className="spinner" aria-hidden="true" />
      <p>Checking your account…</p>
    </main>
  );
}

export function AuthError() {
  const { error, retry } = useAuth();
  return (
    <main className="route-status">
      <p className="form-alert" role="alert">{error}</p>
      <button className="button button--primary" onClick={retry} type="button">
        <RefreshCw size={17} aria-hidden="true" /> Try again
      </button>
    </main>
  );
}

export function NotFound() {
  return (
    <main className="route-status">
      <h1>Page not found</h1>
      <Link to="/" className="text-link">Back to home</Link>
    </main>
  );
}
