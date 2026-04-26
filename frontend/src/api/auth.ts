import { apiClient, API_BASE } from "./client";
import type {
  LoginRequest,
  TokenResponse,
  ApiKeyInfo,
  ApiKeyCreated,
  ApiKeyRequest,
  User,
  CreateUserRequest,
} from "./types";

export async function login(data: LoginRequest): Promise<TokenResponse> {
  const res = await apiClient.post<TokenResponse>(`${API_BASE}/auth/login`, data);
  return res.data;
}

export async function refreshToken(token: string): Promise<TokenResponse> {
  const res = await apiClient.post<TokenResponse>(`${API_BASE}/auth/refresh`, {
    refresh_token: token,
  });
  return res.data;
}

export async function listApiKeys(): Promise<ApiKeyInfo[]> {
  const res = await apiClient.get<ApiKeyInfo[]>(`${API_BASE}/auth/keys`);
  return res.data;
}

export async function createApiKey(
  data: ApiKeyRequest
): Promise<ApiKeyCreated> {
  const res = await apiClient.post<ApiKeyCreated>(`${API_BASE}/auth/keys`, data);
  return res.data;
}

export async function revokeApiKey(keyId: string): Promise<void> {
  await apiClient.delete(`${API_BASE}/auth/keys/${keyId}`);
}

// User management (backend endpoints not yet implemented — will 404 gracefully)
export async function listUsers(): Promise<User[]> {
  const res = await apiClient.get<User[]>(`${API_BASE}/auth/users`);
  return res.data;
}

export async function createUser(data: CreateUserRequest): Promise<User> {
  const res = await apiClient.post<User>(`${API_BASE}/auth/users`, data);
  return res.data;
}

export async function updateUser(
  username: string,
  data: Partial<{ is_active: boolean; role: string }>
): Promise<User> {
  const res = await apiClient.patch<User>(`${API_BASE}/auth/users/${username}`, data);
  return res.data;
}

export async function resetPassword(
  username: string
): Promise<{ temporary_password: string }> {
  const res = await apiClient.post<{ temporary_password: string }>(
    `${API_BASE}/auth/users/${username}/reset-password`
  );
  return res.data;
}
