import { apiClient } from "./client";
import type { AuditLogEntry, AuditLogListResponse } from "./types";

export interface AuditListParams {
  limit?: number;
  offset?: number;
  identity?: string;
  method?: string;
  path_contains?: string;
  status_code?: number;
  from_ts?: number;
  to_ts?: number;
}

export async function listAuditLogs(
  params: AuditListParams
): Promise<AuditLogListResponse> {
  const res = await apiClient.get<AuditLogListResponse>("/api/audit/logs", {
    params,
  });
  return res.data;
}

export async function getAuditLog(logId: number): Promise<AuditLogEntry> {
  const res = await apiClient.get<AuditLogEntry>(`/api/audit/logs/${logId}`);
  return res.data;
}
