import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { ApiError, api } from "../services/api";
import type { AuthPayload, RegisterPayload, User } from "../types";

type AuthStatus = "loading" | "authenticated" | "unauthenticated" | "error";

interface AuthContextValue {
  user: User | null;
  status: AuthStatus;
  error: string | null;
  login: (payload: AuthPayload) => Promise<void>;
  register: (payload: RegisterPayload) => Promise<void>;
  logout: () => Promise<void>;
  retry: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let active = true;
    setStatus("loading");
    setError(null);
    api
      .currentUser()
      .then((currentUser) => {
        if (!active) return;
        setUser(currentUser);
        setStatus("authenticated");
      })
      .catch((cause: unknown) => {
        if (!active) return;
        if (cause instanceof ApiError && cause.status === 401) {
          setUser(null);
          setStatus("unauthenticated");
          return;
        }
        setError(cause instanceof Error ? cause.message : "Unable to verify your session.");
        setStatus("error");
      });
    return () => {
      active = false;
    };
  }, [attempt]);

  const login = useCallback(async (payload: AuthPayload) => {
    const authenticatedUser = await api.login(payload);
    setUser(authenticatedUser);
    setStatus("authenticated");
    setError(null);
  }, []);

  const register = useCallback(async (payload: RegisterPayload) => {
    const authenticatedUser = await api.register(payload);
    setUser(authenticatedUser);
    setStatus("authenticated");
    setError(null);
  }, []);

  const logout = useCallback(async () => {
    await api.logout();
    setUser(null);
    setStatus("unauthenticated");
    setError(null);
  }, []);

  const retry = useCallback(() => setAttempt((value) => value + 1), []);
  const value = useMemo(
    () => ({ user, status, error, login, register, logout, retry }),
    [user, status, error, login, register, logout, retry],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
