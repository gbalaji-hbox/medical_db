import axios from "axios";

// BASE_URL is set by Vite from the `base` config option (VITE_BASE_PATH env var).
// In dev it is '/', in production it matches the sub-path (e.g. '/emr/').
const BASE_URL = import.meta.env.BASE_URL.replace(/\/$/, ''); // '/emr' or ''

export const apiClient = axios.create({
  baseURL: "",
  headers: { "Content-Type": "application/json" },
});

// Prepend the sub-path prefix so all absolute API paths work under any mount point.
// Runs before the auth interceptor so the URL is correct before the token is attached.
apiClient.interceptors.request.use((config) => {
  if (BASE_URL && config.url && !config.url.startsWith(BASE_URL)) {
    config.url = BASE_URL + config.url;
  }
  return config;
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
    const res = await axios.post(`${BASE_URL}/api/auth/refresh`, { refresh_token: rt });
    setAccessToken(res.data.access_token);
    setRefreshToken(res.data.refresh_token);
    return true;
  } catch {
    clearTokens();
    return false;
  }
}
