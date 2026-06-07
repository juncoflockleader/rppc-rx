"use client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import useSWR from "swr";
import {
  ApiException,
  exportEpisode,
  fetchBlobUrl,
  getCost,
  getLatestExport,
  getNotices,
  submitFeedback,
} from "@/lib/api";
import type { Cost, ExportInfo, Notices } from "@/lib/types";
import { useJob } from "@/lib/useJob";
import { Badge, Button, Card, ErrorNote, ProgressBar } from "@/components/ui";

export default function ExportPage() {
  const { id } = useParams<{ id: string }>();
  const exportSWR = useSWR<ExportInfo | null>(`export:${id}`, () =>
    getLatestExport(id).catch(() => null)
  );
  const costSWR = useSWR<Cost | null>(`cost:${id}`, () =>
    getCost(id).catch(() => null)
  );
  const notices = useSWR<Notices>("/api/meta/notices", getNotices);
  const exp = exportSWR.data ?? null;
  const cost = costSWR.data ?? null;
  const [err, setErr] = useState<string | null>(null);

  const job = useJob(() => exportSWR.mutate());

  async function runExport() {
    setErr(null);
    try {
      const { job_id } = await exportEpisode(id);
      job.start(job_id);
    } catch (e) {
      setErr(e instanceof ApiException ? e.message : "Could not start export.");
    }
  }

  async function download() {
    if (!exp) return;
    try {
      const url = await fetchBlobUrl(exp.download_url);
      const a = document.createElement("a");
      a.href = url;
      a.download = `episode_${id}.zip`;
      a.click();
    } catch (e) {
      setErr(e instanceof ApiException ? e.message : "Download failed.");
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <Link
          href={`/episodes/${id}/audio`}
          className="text-sm text-neutral-500 hover:text-neutral-900"
        >
          ← Audio
        </Link>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight">Export</h1>
      </div>

      <Card className="flex flex-wrap items-center justify-between gap-3">
        <div className="text-sm text-neutral-600">
          {exp
            ? `Package ready — ${exp.manifest.files.length} files${exp.manifest.has_audio ? " incl. audio" : ""}.`
            : "Bundle transcript, SRT, show notes, evidence report, and audio into a zip."}
        </div>
        <div className="flex items-center gap-2">
          {exp && (
            <Button variant="secondary" onClick={download}>
              Download .zip
            </Button>
          )}
          <Button onClick={runExport} disabled={job.running}>
            {job.running ? "Packaging…" : exp ? "Re-export" : "Export"}
          </Button>
        </div>
      </Card>

      {job.running && <ProgressBar value={job.job?.progress ?? 0} />}
      <ErrorNote message={err} />

      {exp && (
        <Card>
          <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-neutral-500">
            Package contents
          </div>
          <ul className="flex flex-wrap gap-2">
            {exp.manifest.files.map((f) => (
              <li key={f}>
                <Badge>{f}</Badge>
              </li>
            ))}
          </ul>
        </Card>
      )}

      {cost && (
        <Card>
          <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-neutral-500">
            Cost (this episode)
          </div>
          <div className="grid grid-cols-2 gap-x-6 gap-y-1 text-sm sm:grid-cols-4">
            <Stat label="LLM calls" value={cost.llm_calls} />
            <Stat label="Input tokens" value={cost.llm_input_tokens} />
            <Stat label="Output tokens" value={cost.llm_output_tokens} />
            <Stat label="TTS calls" value={cost.tts_calls} />
            <Stat
              label="Est. LLM cost"
              value={`$${cost.estimated_llm_cost_usd.toFixed(4)}`}
            />
          </div>
        </Card>
      )}

      <FeedbackCard episodeId={id} />

      {notices.data && (
        <p className="text-xs text-neutral-400">
          {notices.data.disclaimer_en} {notices.data.source_copyright}
        </p>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number | string }) {
  return (
    <div>
      <div className="text-neutral-500">{label}</div>
      <div className="font-medium text-neutral-800">{value}</div>
    </div>
  );
}

function FeedbackCard({ episodeId }: { episodeId: string }) {
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);

  async function send(rating: number) {
    setBusy(true);
    try {
      await submitFeedback({
        target_type: "episode",
        target_id: episodeId,
        episode_id: episodeId,
        feedback_type: "thumbs",
        rating,
      });
      setDone(true);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card className="flex items-center justify-between">
      <div className="text-sm text-neutral-600">How was this episode?</div>
      {done ? (
        <span className="text-sm text-neutral-500">Thanks for the feedback.</span>
      ) : (
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => send(1)} disabled={busy}>
            👍
          </Button>
          <Button variant="secondary" onClick={() => send(-1)} disabled={busy}>
            👎
          </Button>
        </div>
      )}
    </Card>
  );
}
