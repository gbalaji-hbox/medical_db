export type Module = "mca" | "hct" | "ssc" | "cam" | "cim" | "xhi";

export const MODULES: Module[] = ["mca", "hct", "ssc", "cam", "cim", "xhi"];

export const MODULE_LABELS: Record<Module, string> = {
  mca: "MCA",
  hct: "HCT",
  ssc: "SSC",
  cam: "CAM",
  cim: "CIM",
  xhi: "XHI",
};

export const MODULE_CLINIC_NAMES: Record<Module, string> = {
  mca: "Midwest Cardiology Associates",
  hct: "Heart Center Of North Texas",
  ssc: "Sun State Cardiology",
  cam: "Cardiology Associates of Michigan",
  cim: "Cardiology Institute of Michigan",
  xhi: "Xavier Heart Institute",
};

export const MODULE_DESCRIPTIONS: Record<Module, string> = {
  mca: "Midwest Cardiology Associates · Aprima",
  hct: "Heart Center Of North Texas · NextGen",
  ssc: "Sun State Cardiology · Athena",
  cam: "Cardiology Associates of Michigan · EPIC (Henry Ford)",
  cim: "Cardiology Institute of Michigan · EPIC (Henry Ford)",
  xhi: "Xavier Heart Institute · DrChrono",
};

export type JobStatus =
  | "pending"
  | "running"
  | "done"
  | "error"
  | "queued"
  | "failed";

export interface Job {
  job_id: string;
  module: Module;
  status: JobStatus;
  created_at: number;
  started_at: number | null;
  finished_at: number | null;
  returncode: number | null;
  log: string;
  output_file: string | null;
  submitted_by: string | null;
}

export interface JobCreated {
  job_id: string;
  module: Module;
  status: string;
  message: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface ApiKeyInfo {
  key_id: string;
  name: string;
  created_by: string;
  created_at: number;
  last_used_at: number | null;
  is_active: boolean;
  role: string;
}

export interface ApiKeyCreated {
  key_id: string;
  key: string;
  name: string;
  role: string;
  message: string;
}

export interface ApiKeyRequest {
  name: string;
  role?: string;
}

export interface ModuleInfo {
  name: string;
  description: string;
  required_files: string[];
  optional_files?: string[];
}

export interface AuditLogEntry {
  id: number;
  ts: number;
  identity: string | null;
  auth_type: string | null;
  method: string;
  path: string;
  status_code: number | null;
  duration_ms: number | null;
  client_ip: string | null;
}

export interface AuditLogListResponse {
  total: number;
  limit: number;
  offset: number;
  items: AuditLogEntry[];
}

export interface User {
  username: string;
  role: "admin" | "user";
  created_at: number;
  is_active: boolean;
  api_key_count: number;
}

export interface CreateUserRequest {
  username: string;
  password: string;
  role: "admin" | "user";
}
