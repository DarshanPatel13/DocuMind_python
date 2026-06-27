import { createContext, useContext, useMemo, useState, type ReactNode } from "react";

import { login as loginRequest } from "../api/documind";
import { clearToken, getToken, setToken } from "./token";

interface AuthState {
  isAuthenticated: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setTokenState] = useState<string | null>(() => getToken());

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
