"use client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useRef, useState } from "react";
import useSWR from "swr";
import {
  ApiException,
  createTextSource,
  fetcher,
  getSourceSummary,
  processSource,
  uploadSource,
} from "@/lib/api";
import type { Project, Source, SourceSummary } from "@/lib/types";
import { useJob } from "@/lib/useJob";
import {
  Badge,
  Button,
  Card,
  ErrorNote,
  ProgressBar,
  statusTone,
} from "@/components/ui";

export default function ProjectDetailPage() {
  const { id } = useParams<{ id: string }>();
  const project = useSWR<Project>(`/api/projects/${id}`, fetcher);
  const sources = useSWR<Source[]>(`/api/projects/${id}/sources`, fetcher);

  return (
    <div className="space-y-6">
      <div>
        <Link href="/projects" className="text-sm text-neutral-500 hover:text-neutral-900">
          ← Projects
        </Link>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight">
          {project.data?.title ?? "Project"}
        </h1>
      </div>

      <AddSource projectId={id} onAdded={() => sources.mutate()} />

      <section className="space-y-3">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-neutral-500">
          Sources
        </h2>
        {sources.error && <ErrorNote message="Could not load sources." />}
        {sources.data?.length === 0 && (
          <p className="text-sm text-neutral-500">
            No sources yet. Paste or upload material above.
          </p>
        )}
        {sources.data?.map((s) => (
          <SourceCard key={s.id} projectId={id} source={s} onChange={() => sources.mutate()} />
        ))}
      </section>
    </div>
  );
}

function AddSource({
  projectId,
  onAdded,
}: {
  projectId: string;
  onAdded: () => void;
}) {
  const [text, setText] = useState("");
  const [title, setTitle] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  async function addText(e: React.FormEvent) {
    e.preventDefault();
    if (!text.trim()) return;
    setBusy(true);
    setErr(null);
    try {
      await createTextSource(projectId, { title: title.trim() || undefined, text });
      setText("");
      setTitle("");
      onAdded();
    } catch (e) {
      setErr(e instanceof ApiException ? e.message : "Failed to add source.");
    } finally {
      setBusy(false);
    }
  }

  async function onFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setBusy(true);
    setErr(null);
    try {
      await uploadSource(projectId, file);
      onAdded();
    } catch (e) {
      setErr(e instanceof ApiException ? e.message : "Upload failed.");
    } finally {
      setBusy(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  return (
    <Card className="space-y-3">
      <form onSubmit={addText} className="space-y-2">
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Source title (optional)"
          className="w-full rounded-md border border-neutral-300 px-3 py-1.5 text-sm outline-none focus:border-neutral-900"
        />
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Paste an essay or notes…"
          rows={4}
          className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm outline-none focus:border-neutral-900"
        />
        <div className="flex items-center gap-3">
          <Button type="submit" disabled={busy || !text.trim()}>
            Add text source
          </Button>
          <span className="text-xs text-neutral-400">or</span>
          <label className="cursor-pointer text-sm text-neutral-600 hover:text-neutral-900">
            <input
              ref={fileRef}
              type="file"
              accept=".txt,.md,.pdf"
              onChange={onFile}
              className="hidden"
            />
            Upload .txt / .md / .pdf
          </label>
        </div>
      </form>
      <ErrorNote message={err} />
    </Card>
  );
}

function SourceCard({
  projectId,
  source,
  onChange,
}: {
  projectId: string;
  source: Source;
  onChange: () => void;
}) {
  const [summary, setSummary] = useState<SourceSummary | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const { job, running, start } = useJob(async () => {
    onChange();
    await loadSummary();
  });

  async function loadSummary() {
    try {
      setSummary(await getSourceSummary(source.id));
    } catch {
      /* summary not ready */
    }
  }

  async function process() {
    setErr(null);
    try {
      const { job_id } = await processSource(projectId, source.id);
      start(job_id);
    } catch (e) {
      setErr(e instanceof ApiException ? e.message : "Could not start processing.");
    }
  }

  const status = job?.status === "completed" ? "processed" : source.status;

  return (
    <Card className="space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <div className="font-medium">
            {source.title || source.type}{" "}
            <span className="text-xs text-neutral-400">({source.type})</span>
          </div>
          <div className="text-xs text-neutral-500">{source.id}</div>
        </div>
        <div className="flex items-center gap-2">
          <Badge tone={statusTone(status)}>{status}</Badge>
          {status !== "processed" && (
            <Button variant="secondary" onClick={process} disabled={running}>
              {running ? "Processing…" : "Process"}
            </Button>
          )}
          {status === "processed" && !summary && (
            <Button variant="ghost" onClick={loadSummary}>
              View summary
            </Button>
          )}
        </div>
      </div>

      {running && job && (
        <div className="space-y-1">
          <ProgressBar value={job.progress} />
          <div className="text-xs text-neutral-500">
            {job.job_type} — {Math.round(job.progress * 100)}%
          </div>
        </div>
      )}
      {job?.status === "failed" && (
        <ErrorNote message={job.error?.message ?? "Processing failed."} />
      )}
      <ErrorNote message={err} />

      {summary && <SummaryView summary={summary} />}
    </Card>
  );
}

function SummaryView({ summary }: { summary: SourceSummary }) {
  return (
    <div className="space-y-3 rounded-md bg-neutral-50 p-3">
      {summary.summary && (
        <p className="text-sm text-neutral-700">{summary.summary}</p>
      )}
      {summary.themes.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {summary.themes.map((t) => (
            <Badge key={t} tone="blue">
              {t}
            </Badge>
          ))}
        </div>
      )}
      {summary.claims.length > 0 && (
        <div>
          <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-neutral-500">
            Key claims
          </div>
          <ul className="space-y-1">
            {summary.claims.map((c) => (
              <li key={c.claim_id} className="text-sm text-neutral-700">
                <span className="text-neutral-400">•</span> {c.claim_text}{" "}
                {c.claim_type && (
                  <span className="text-xs text-neutral-400">({c.claim_type})</span>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
