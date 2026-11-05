import React, { useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { LogIn, AlertCircle, ArrowRight, Sparkles } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import MascotBadge from '../components/common/MascotBadge';

export const LoginPage: React.FC = () => {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      await login({ email, password });
      navigate('/app/overview');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Invalid login credentials.');
    } finally {
      setIsLoading(false);
    }
  };

  const fillDemo = () => {
    setEmail('patient@example.com');
    setPassword('DemoPassword123!');
  };

  return (
    <div className="min-h-screen bg-[#F7F7FB] flex flex-col justify-center items-center p-6 text-[#292443]">
      <div className="w-full max-w-md">
        {/* Header Branding */}
        <div className="text-center mb-8">
          <MascotBadge size="md" showTagline className="justify-center" />
          <h2 className="mt-4 text-2xl font-bold tracking-tight">Sign in to your Medical Workspace</h2>
          <p className="mt-1 text-xs text-[#77758A]">
            Access your private, evidence-grounded medical records.
          </p>
        </div>

        {/* Card Form */}
        <div className="bg-white p-8 rounded-2xl border border-[#E8E7F0] shadow-sm">
          {error && (
            <div className="mb-5 p-3 rounded-xl bg-red-50 border border-red-200 text-xs text-[#C93636] flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-[#292443] mb-1.5">
                Email Address
              </label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@example.com"
                className="w-full px-3.5 py-2.5 rounded-xl border border-[#E8E7F0] text-sm focus:border-[#6257F5] focus:ring-2 focus:ring-[#6257F5]/20 focus-ring transition bg-white"
              />
            </div>

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="block text-xs font-semibold text-[#292443]">
                  Password
                </label>
                <NavLink
                  to="/forgot-password"
                  className="text-xs text-[#6257F5] hover:underline"
                >
                  Forgot password?
                </NavLink>
              </div>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full px-3.5 py-2.5 rounded-xl border border-[#E8E7F0] text-sm focus:border-[#6257F5] focus:ring-2 focus:ring-[#6257F5]/20 focus-ring transition bg-white"
              />
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full mt-2 py-3 px-4 rounded-xl bg-[#6257F5] hover:bg-[#5148d4] text-white font-semibold text-sm transition shadow-sm shadow-violet-500/20 flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {isLoading ? (
                <span>Signing in...</span>
              ) : (
                <>
                  <LogIn className="w-4 h-4" />
                  <span>Sign In</span>
                </>
              )}
            </button>
          </form>

          {/* Demo account quick fill */}
          <div className="mt-6 pt-5 border-t border-[#E8E7F0] text-center">
            <button
              type="button"
              onClick={fillDemo}
              className="inline-flex items-center gap-1.5 text-xs font-medium text-[#6257F5] hover:text-[#5148d4] bg-[#F0EEFF] px-3 py-1.5 rounded-lg border border-[#6257F5]/20 transition"
            >
              <Sparkles className="w-3.5 h-3.5 text-[#22B8B0]" />
              <span>Fill demo test credentials</span>
            </button>
          </div>
        </div>

        {/* Footer links */}
        <p className="mt-6 text-center text-xs text-[#77758A]">
          Don&apos;t have an account yet?{' '}
          <NavLink to="/register" className="font-semibold text-[#6257F5] hover:underline">
            Create account
          </NavLink>
        </p>
      </div>
    </div>
  );
};

export default LoginPage;

