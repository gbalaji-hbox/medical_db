import axios from "axios";

// In production nginx proxies /api/* to the backend on the same origin.
// In dev, vite.config.ts proxies /api/* to localhost:8000.
// No absolute base URL needed in either environment.
export const apiClient = axios.create({
  baseURL: "",
  headers: { "Content-Type": "application/json" },
});

// Attach access token from memory on every request
apiClient.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Silent refresh on 401
apiClient.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config;
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;
      const refreshed = await attemptRefresh();
      if (refreshed) {
        original.headers.Authorization = `Bearer ${getAccessToken()}`;
        return apiClient(original);
      }
    }
    return Promise.reject(error);
  }
);

// In-memory access token (cleared on page reload — intentional security trade-off)
let _accessToken: string | null = null;

export function setAccessToken(token: string | null) {
  _accessToken = token;
}
export function getAccessToken() {
  return _accessToken;
}

export function setRefreshToken(token: string) {
  localStorage.setItem("refresh_token", token);
}
export function getRefreshToken() {
  return localStorage.getItem("refresh_token");
}
export function clearTokens() {
  _accessToken = null;
  localStorage.removeItem("refresh_token");
}

async function attemptRefresh(): Promise<boolean> {
  const rt = getRefreshToken();
  if (!rt) return false;
  try {
    const res = await axios.post("/api/auth/refresh", { refresh_token: rt });
    setAccessToken(res.data.access_token);
    setRefreshToken(res.data.refresh_token);
    return true;
  } catch {
    clearTokens();
    return false;
  }
}
