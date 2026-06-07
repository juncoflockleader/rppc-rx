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

// --- Personas ---
export type PersonaCard = {
  persona_id: string;
  version: string;
  display_name?: string | null;
  type?: string | null;
  status?: string | null;
  summary?: string | null;
};

export type PersonaVersion = {
  persona_id: string;
  version: string;
  display_name?: string | null;
  type?: string | null;
  status?: string | null;
  identity_profile?: { summary?: string; disclaimer?: string } & Record<string, unknown>;
  stance_matrix?: Record<string, { position?: string } | unknown>;
  style_profile?: Record<string, unknown>;
  forbidden_moves?: string[];
  voice_profile?: Record<string, unknown>;
  release_notes?: string | null;
};

// --- Episodes / planning ---
export type EpisodeParticipant = {
  persona_id: string;
  version: string;
  role: string;
  speaker_label: string;
};

export type Episode = {
  id: string;
  project_id: string;
  title?: string | null;
  status: string;
  target_language: string;
  target_duration_seconds: number;
  format: string;
  participants: EpisodeParticipant[];
};

export type Beat = {
  beat_id: string;
  title: string;
  goal: string;
  primary_speaker?: string;
  target_seconds: number;
  source_claim_ids?: string[];
  persona_concepts?: string[];
};

export type DiscussionPlan = {
  episode_id: string;
  version: number;
  status: string;
  plan: { title?: string; beats: Beat[]; ending?: { takeaway?: string } };
};

export type RoleContextCard = {
  persona_id?: string;
  episode_position?: string;
  relevant_source_claim_ids?: string[];
  relevant_persona_concepts?: string[];
  likely_agreements?: string[];
  likely_tensions?: string[];
  style_reminders?: string[];
  forbidden_moves?: string[];
};

export type RoleContext = {
  episode_id: string;
  cards: { speaker_label: string; version: number; card: RoleContextCard }[];
};

// --- Script + QA ---
export type EvidenceType =
  | "source_material"
  | "persona_canon"
  | "host_bridge"
  | "creative_bridge"
  | "unsupported_or_needs_review";

export type Evidence = {
  type: EvidenceType;
  claim_id?: string | null;
  concept?: string | null;
  notes?: string | null;
};

export type ScriptSegment = {
  id: string;
  segment_index: number;
  beat_id?: string | null;
  speaker_label: string;
  text: string;
  estimated_seconds: number;
  status: string;
  evidence: Evidence[];
};

export type Script = {
  episode_id: string;
  script_version_id: string;
  version: number;
  status: string;
  safety_status: string;
  total_estimated_seconds?: number | null;
  metadata?: { speaker_share?: Record<string, number>; segment_count?: number } | null;
  segments: ScriptSegment[];
};

export type Severity = "low" | "medium" | "high";

export type QaWarning = {
  segment_id?: string | null;
  segment_index?: number | null;
  speaker_label?: string | null;
  severity: Severity;
  message: string;
  suggested_action?: string;
  suggested_rewrite?: string;
};

export type QaReport = {
  report_type: string;
  score: Record<string, unknown>;
  warnings: QaWarning[];
};

export type QaPanel = {
  script_version_id: string;
  safety_status: string;
  summary: Record<string, number | null>;
  reports: QaReport[];
};

export type SegmentUpdate = {
  id: string;
  text: string;
  estimated_seconds: number;
  status: string;
};

// --- Audio / export / cost / feedback ---
export type AudioMix = {
  episode_id: string;
  mix_id: string;
  status: string; // completed | stale
  format: string;
  duration_ms?: number | null;
  download_url: string;
};

export type ExportInfo = {
  episode_id: string;
  export_id: string;
  format: string;
  manifest: { files: string[]; has_audio: boolean; segment_count: number };
  download_url: string;
};

export type Cost = {
  llm_input_tokens: number;
  llm_output_tokens: number;
  llm_calls: number;
  tts_chars: number;
  tts_duration_ms: number;
  tts_calls: number;
  estimated_llm_cost_usd: number;
};

export type Notices = {
  disclaimer_en: string;
  disclaimer_zh: string;
  source_copyright: string;
};
