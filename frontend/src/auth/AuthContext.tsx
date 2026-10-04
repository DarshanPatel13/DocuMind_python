import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { login as loginRequest } from "../api/documind";
import { UNAUTHORIZED_EVENT, clearToken, getToken, setToken } from "./token";

interface AuthState {
  isAuthenticated: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setTokenState] = useState<string | null>(() => getToken());

  // The API layer fires this on a 401 (expired/invalid token): sign out.
  useEffect(() => {
    const onUnauthorized = () => setTokenState(null);
    window.addEventListener(UNAUTHORIZED_EVENT, onUnauthorized);
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, onUnauthorized);
  }, []);

  const value = useMemo<AuthState>(
    () => ({
      isAuthenticated: Boolean(token),
      async login(username, password) {
        const { access_token } = await loginRequest(username, password);
        setToken(access_token);
        setTokenState(access_token);
      },
      logout() {
        clearToken();
        setTokenState(null);
      },
    }),
    [token],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within <AuthProvider>");
  return ctx;
}
