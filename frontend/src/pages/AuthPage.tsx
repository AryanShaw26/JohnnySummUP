import { ArrowLeft, ArrowRight, Eye, EyeOff, LockKeyhole, Mail, UserRound } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { BrandLogo } from "../components/common/BrandLogo";
import { useAuth } from "../hooks/useAuth";
import { ApiError } from "../services/api";

interface AuthPageProps {
  mode: "login" | "register";
}

export function AuthPage({ mode }: AuthPageProps) {
  const isRegister = mode === "register";
  const { status, login, register } = useAuth();
  const navigate = useNavigate();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (status === "authenticated") {
    return <Navigate to="/app" replace />;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    if (isRegister && password !== confirmPassword) {
      setError("Your passwords don’t match. Please check and try again.");
      return;
    }
    setSubmitting(true);
    try {
      if (isRegister) {
        await register({ full_name: fullName.trim(), email: email.trim(), password });
      } else {
        await login({ email: email.trim(), password });
      }
      navigate("/app", { replace: true });
    } catch (cause) {
      if (cause instanceof ApiError && cause.status === 401) {
        setError("That email and password combination doesn’t match. Please try again.");
      } else if (cause instanceof ApiError && cause.status === 409) {
        setError("An account with this email already exists. Try logging in instead.");
      } else {
        setError(cause instanceof Error ? cause.message : "Something went wrong. Please try again.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="auth-page">
      <Link className="auth-back" to="/"><ArrowLeft size={17} aria-hidden="true" /> Back to home</Link>
      <section className="auth-card" aria-labelledby="auth-title">
        <div className="auth-card__brand"><BrandLogo /></div>
        <div className="auth-card__heading">
          <p className="eyebrow">{isRegister ? "A FRESH START" : "WELCOME BACK"}</p>
          <h1 id="auth-title">{isRegister ? "Create your account" : "Good to see you again."}</h1>
          <p>{isRegister ? "A few details and you’re on your way." : "Log in to continue to your workspace."}</p>
        </div>
        <form className="auth-form" onSubmit={handleSubmit}>
          {isRegister && (
            <label className="field">
              <span>Full name</span>
              <span className="field__control"><UserRound size={17} aria-hidden="true" /><input autoComplete="name" name="name" required maxLength={150} value={fullName} onChange={(event) => setFullName(event.target.value)} placeholder="Your name" /></span>
            </label>
          )}
          <label className="field">
            <span>Email address</span>
            <span className="field__control"><Mail size={17} aria-hidden="true" /><input autoComplete="email" name="email" type="email" required maxLength={254} value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@example.com" /></span>
          </label>
          <label className="field">
            <span>Password</span>
            <span className="field__control"><LockKeyhole size={17} aria-hidden="true" /><input autoComplete={isRegister ? "new-password" : "current-password"} name="password" type={showPassword ? "text" : "password"} required minLength={isRegister ? 8 : 1} maxLength={128} value={password} onChange={(event) => setPassword(event.target.value)} placeholder={isRegister ? "At least 8 characters" : "Your password"} /><button type="button" className="field__toggle" onClick={() => setShowPassword((shown) => !shown)} aria-label={showPassword ? "Hide password" : "Show password"}>{showPassword ? <EyeOff size={17} /> : <Eye size={17} />}</button></span>
          </label>
          {isRegister && (
            <label className="field">
              <span>Confirm password</span>
              <span className="field__control"><LockKeyhole size={17} aria-hidden="true" /><input autoComplete="new-password" name="confirm-password" type={showPassword ? "text" : "password"} required minLength={8} maxLength={128} value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} placeholder="Enter your password again" /></span>
            </label>
          )}
          {error && <p className="form-alert" role="alert">{error}</p>}
          {isRegister && <p className="form-hint">Use at least 8 characters. Your password is securely hashed before it is stored.</p>}
          <button className="button button--primary button--large auth-form__submit" type="submit" disabled={submitting}>
            {submitting ? "Please wait…" : isRegister ? "Create account" : "Log in"}
            {!submitting && <ArrowRight size={18} aria-hidden="true" />}
          </button>
        </form>
        <p className="auth-card__switch">
          {isRegister ? "Already have an account?" : "New to JohnnySummUP?"}{" "}
          <Link to={isRegister ? "/login" : "/register"}>{isRegister ? "Log in" : "Create an account"}</Link>
        </p>
      </section>
      <p className="auth-page__footnote">A thoughtful beginning. More to come.</p>
    </main>
  );
}
