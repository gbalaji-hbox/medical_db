import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  useRef,
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
  showTimeoutWarning?: boolean;
  extendSession?: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

// Session timeout configuration (30 minutes of inactivity)
const SESSION_TIMEOUT_MS = 30 * 60 * 1000; // 30 minutes
const WARNING_TIME_MS = 5 * 60 * 1000; // Show warning 5 minutes before timeout

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
  const [showTimeoutWarning, setShowTimeoutWarning] = useState(false);
  
  const timeoutRef = useRef<number | undefined>(undefined);
  const warningRef = useRef<number | undefined>(undefined);
  const lastActivityRef = useRef<number>(Date.now());

  const logout = useCallback(() => {
    clearTokens();
    setUser(null);
    setShowTimeoutWarning(false);
    
    // Clear timers
    if (timeoutRef.current) clearTimeout(timeoutRef.current!);
    if (warningRef.current) clearTimeout(warningRef.current!);
  }, []);

  const resetTimeout = useCallback(() => {
    lastActivityRef.current = Date.now();
    setShowTimeoutWarning(false);
    
    // Clear existing timers
    if (timeoutRef.current) clearTimeout(timeoutRef.current!);
    if (warningRef.current) clearTimeout(warningRef.current!);
    
    // Set warning timer (25 minutes from now)
    warningRef.current = setTimeout(() => {
      setShowTimeoutWarning(true);
    }, SESSION_TIMEOUT_MS - WARNING_TIME_MS);
    
    // Set logout timer (30 minutes from now)
    timeoutRef.current = setTimeout(() => {
      logout();
    }, SESSION_TIMEOUT_MS);
  }, [logout]);

  const applyToken = useCallback((access: string) => {
    setAccessToken(access);
    const payload = parseJwt(access);
    if (payload) {
      setUser({
        username: payload.sub as string,
        role: (payload.role as "admin" | "user") ?? "user",
      });
      resetTimeout(); // Start/reset timeout when user logs in
    }
  }, [resetTimeout]);

  // Activity event handlers
  const handleActivity = useCallback(() => {
    if (user) {
      resetTimeout();
    }
  }, [user, resetTimeout]);

  // Set up activity listeners
  useEffect(() => {
    const events = ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart', 'click'];
    
    const handleEvent = () => handleActivity();
    
    events.forEach(event => {
      document.addEventListener(event, handleEvent, true);
    });
    
    return () => {
      events.forEach(event => {
        document.removeEventListener(event, handleEvent, true);
      });
    };
  }, [handleActivity]);

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
      .catch((err) => {
        // Only wipe tokens when the server explicitly rejects them (401).
        // Transient failures (network, 429 rate-limit, 5xx) should leave the
        // refresh token intact so the next page load can retry.
        const status = err?.response?.status;
        if (status === 401) clearTokens();
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

  // Extend the AuthState interface to include timeout warning
  const authState: AuthState & { showTimeoutWarning: boolean; extendSession: () => void } = {
    user,
    isLoading,
    login,
    logout,
    showTimeoutWarning,
    extendSession: resetTimeout,
  };

  return (
    <AuthContext.Provider value={authState as AuthState}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
