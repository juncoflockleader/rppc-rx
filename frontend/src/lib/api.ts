// Typed client for the Podcast Synthesis backend. Sends the dev bearer token
// and unwraps the backend's {error:{message}} envelope into thrown Errors.
import type {
  Job,
  JobRef,
  Project,
  Source,
  SourceSummary,
} from "./types";

const BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";
const TOKEN = process.env.NEXT_PUBLIC_DEV_TOKEN ?? "dev-token";

export class ApiException extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${TOKEN}`,
      ...(init?.body && !(init.body instanceof FormData)
        ? { "Content-Type": "application/json" }
        : {}),
      ...(init?.headers ?? {}),
    },
  });
  if (res.status === 204) return undefined as T;
  const text = await res.text();
  const data = text ? JSON.parse(text) : undefined;
  if (!res.ok) {
    const msg =
      data?.error?.message ?? data?.detail ?? `Request failed (${res.status})`;
    throw new ApiException(res.status, msg);
  }
  return data as T;
}

// SWR fetcher
export const fetcher = <T>(path: string) => request<T>(path);

// --- Projects ---
export const listProjects = () => request<Project[]>("/api/projects");
export const getProject = (id: string) =>
  request<Project>(`/api/projects/${id}`);
export const createProject = (body: {
  title: string;
  description?: string;
  default_language?: string;
}) =>
  request<Project>("/api/projects", {
    method: "POST",
    body: JSON.stringify(body),
  });
export const deleteProject = (id: string) =>
  request<void>(`/api/projects/${id}`, { method: "DELETE" });

// --- Sources ---
export const listSources = (projectId: string) =>
  request<Source[]>(`/api/projects/${projectId}/sources`);
export const createTextSource = (
  projectId: string,
  body: { title?: string; text: string }
) =>
  request<Source>(`/api/projects/${projectId}/sources/text`, {
    method: "POST",
    body: JSON.stringify(body),
  });
export const uploadSource = (projectId: string, file: File) => {
  const fd = new FormData();
  fd.append("file", file);
  return request<Source>(`/api/projects/${projectId}/sources`, {
    method: "POST",
    body: fd,
  });
};
export const processSource = (projectId: string, sourceId: string) =>
  request<JobRef>(`/api/projects/${projectId}/sources/${sourceId}/process`, {
    method: "POST",
  });
export const getSourceSummary = (sourceId: string) =>
  request<SourceSummary>(`/api/sources/${sourceId}/summary`);

// --- Jobs ---
export const getJob = (jobId: string) => request<Job>(`/api/jobs/${jobId}`);
