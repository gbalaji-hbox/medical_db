import { apiClient } from "./client";
import type { Job, JobCreated, Module } from "./types";

export interface JobsFilter {
  module?: Module;
  status?: string;
  page?: number;
  limit?: number;
}

export async function listJobs(filter?: JobsFilter): Promise<Job[]> {
  const res = await apiClient.get<Job[]>("/api/jobs", { params: filter });
  return res.data;
}

export async function getJob(module: Module, jobId: string): Promise<Job> {
  const res = await apiClient.get<Job>(`/api/${module}/jobs/${jobId}`);
  return res.data;
}

export async function runExisting(module: Module): Promise<JobCreated> {
  const res = await apiClient.post<JobCreated>(`/api/${module}/run-existing`);
  return res.data;
}

export async function processFiles(
  module: Module,
  files: Record<string, File>
): Promise<JobCreated> {
  const form = new FormData();
  for (const [field, file] of Object.entries(files)) {
    form.append(field, file);
  }
  const res = await apiClient.post<JobCreated>(`/api/${module}/process`, form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return res.data;
}

export async function downloadJob(
  module: Module,
  jobId: string
): Promise<Blob> {
  const res = await apiClient.get(`/api/${module}/jobs/${jobId}/download`, {
    responseType: "blob",
  });
  return res.data;
}

export async function listModuleJobs(module: Module): Promise<Job[]> {
  const all = await listJobs();
  return all.filter((j) => j.module === module);
}
