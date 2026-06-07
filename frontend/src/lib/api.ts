// Typed client for the Podcast Synthesis backend. Sends the dev bearer token
// and unwraps the backend's {error:{message}} envelope into thrown Errors.
import type {
  DiscussionPlan,
  Episode,
  EpisodeParticipant,
  Job,
  JobRef,
  PersonaCard,
  PersonaVersion,
  Project,
  RoleContext,
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

// --- Personas ---
export const listPersonas = () => request<PersonaCard[]>("/api/personas");
export const getPersonaVersion = (personaId: string, version: string) =>
  request<PersonaVersion>(`/api/personas/${personaId}/versions/${version}`);

// --- Episodes / planning ---
export const listEpisodes = (projectId: string) =>
  request<Episode[]>(`/api/projects/${projectId}/episodes`);
export const getEpisode = (id: string) => request<Episode>(`/api/episodes/${id}`);
export const createEpisode = (
  projectId: string,
  body: {
    title?: string;
    goal?: string;
    target_duration_seconds?: number;
    personas: EpisodeParticipant[];
  }
) =>
  request<Episode>(`/api/projects/${projectId}/episodes`, {
    method: "POST",
    body: JSON.stringify(body),
  });
export const generatePlan = (episodeId: string) =>
  request<JobRef>(`/api/episodes/${episodeId}/discussion-plan`, { method: "POST" });
export const getPlan = (episodeId: string) =>
  request<DiscussionPlan>(`/api/episodes/${episodeId}/discussion-plan`);
export const getRoleContext = (episodeId: string) =>
  request<RoleContext>(`/api/episodes/${episodeId}/role-context`);

// --- Jobs ---
export const getJob = (jobId: string) => request<Job>(`/api/jobs/${jobId}`);
