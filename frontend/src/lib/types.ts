// Response shapes mirrored from the FastAPI backend (app/schemas.py & routers).

export type Project = {
  id: string;
  title: string;
  description?: string | null;
  status: string;
  default_language: string;
};

export type Source = {
  id: string;
  project_id: string;
  type: string;
  title?: string | null;
  status: string;
};

export type Claim = {
  claim_id: string;
  claim_text: string;
  claim_type?: string | null;
  page_number?: number | null;
  confidence?: number | null;
};

export type SourceSummary = {
  source_id: string;
  status: string;
  summary?: string | null;
  themes: string[];
  claims: Claim[];
};

export type Job = {
  id: string;
  job_type: string;
  status: "queued" | "running" | "completed" | "failed" | "canceled";
  progress: number;
  project_id?: string | null;
  episode_id?: string | null;
  error?: { type?: string; message?: string } | null;
};

export type JobRef = { job_id: string; status: string };

export type ApiError = { error: { type: string; message: string } };
