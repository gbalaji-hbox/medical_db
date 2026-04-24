import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
} from "react";
import type { ReactNode } from "react";
import {
  setAccessToken,
  setRefreshToken,
  clearTokens,
  getRefreshToken,
} from "@/api/client";
import { login as apiLogin, refreshToken as apiRefresh } from "@/api/auth";

interface AuthUser {
  username: string;
  role: "admin" | "user";
}

interface AuthState {
  user: AuthUser | null;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

function parseJwt(token: string): Record<string, unknown> | null {
  try {
    return JSON.parse(atob(token.split(".")[1]));
  } catch {
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const applyToken = useCallback((access: string) => {
    setAccessToken(access);
    const payload = parseJwt(access);
    if (payload) {
      setUser({
        username: payload.sub as string,
        role: (payload.role as "admin" | "user") ?? "user",
      });
    }
  }, []);

  // Restore session from refresh token on mount
  useEffect(() => {
    const rt = getRefreshToken();
    if (!rt) {
      setIsLoading(false);
      return;
    }
    apiRefresh(rt)
      .then((tokens) => {
        applyToken(tokens.access_token);
        setRefreshToken(tokens.refresh_token);
      })
      .catch(() => {
        clearTokens();
      })
      .finally(() => setIsLoading(false));
  }, [applyToken]);

  const login = useCallback(
    async (username: string, password: string) => {
      const tokens = await apiLogin({ username, password });
      applyToken(tokens.access_token);
      setRefreshToken(tokens.refresh_token);
    },
    [applyToken]
  );

  const logout = useCallback(() => {
    clearTokens();
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
