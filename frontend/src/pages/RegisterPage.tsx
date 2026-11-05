import React, { useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { UserPlus, AlertCircle, ShieldCheck } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import MascotBadge from '../components/common/MascotBadge';

export const RegisterPage: React.FC = () => {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [acceptTerms, setAcceptTerms] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!acceptTerms) {
      setError('Please accept the medical disclaimer and privacy terms.');
      return;
    }
    setError(null);
    setIsLoading(true);

    try {
      await register({
        email,
        password,
        fullName,
        acceptTerms: true,
        acceptPrivacy: true,
      });
      navigate('/app/overview');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Registration failed.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#F7F7FB] flex flex-col justify-center items-center p-6 text-[#292443]">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <MascotBadge size="md" showTagline className="justify-center" />
          <h2 className="mt-4 text-2xl font-bold tracking-tight">Create your Medical Workspace</h2>
          <p className="mt-1 text-xs text-[#77758A]">
            Private, evidence-grounded document understanding.
          </p>
        </div>

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
                Full Name
              </label>
              <input
                type="text"
                required
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="Jane Doe"
                className="w-full px-3.5 py-2.5 rounded-xl border border-[#E8E7F0] text-sm focus:border-[#6257F5] focus:ring-2 focus:ring-[#6257F5]/20 focus-ring transition bg-white"
              />
            </div>

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
              <label className="block text-xs font-semibold text-[#292443] mb-1.5">
                Password (min. 6 characters)
              </label>
              <input
                type="password"
                required
                minLength={6}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full px-3.5 py-2.5 rounded-xl border border-[#E8E7F0] text-sm focus:border-[#6257F5] focus:ring-2 focus:ring-[#6257F5]/20 focus-ring transition bg-white"
              />
            </div>

            <div className="pt-2">
              <label className="flex items-start gap-2.5 text-xs text-[#77758A] cursor-pointer">
                <input
                  type="checkbox"
                  checked={acceptTerms}
                  onChange={(e) => setAcceptTerms(e.target.checked)}
                  className="mt-0.5 rounded text-[#6257F5] focus:ring-[#6257F5]"
                />
                <span>
                  I acknowledge that JohnnySummUP is informational only and does not diagnose, prescribe, or replace professional medical advice.
                </span>
              </label>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full mt-2 py-3 px-4 rounded-xl bg-[#6257F5] hover:bg-[#5148d4] text-white font-semibold text-sm transition shadow-sm shadow-violet-500/20 flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {isLoading ? (
                <span>Creating workspace...</span>
              ) : (
                <>
                  <UserPlus className="w-4 h-4" />
                  <span>Create Account</span>
                </>
              )}
            </button>
          </form>
        </div>

        <p className="mt-6 text-center text-xs text-[#77758A]">
          Already have an account?{' '}
          <NavLink to="/login" className="font-semibold text-[#6257F5] hover:underline">
            Sign in
          </NavLink>
        </p>
      </div>
    </div>
  );
};

export default RegisterPage;

