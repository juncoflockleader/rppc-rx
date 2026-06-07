"use client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import useSWR from "swr";
import {
  ApiException,
  fetchBlobUrl,
  getLatestAudio,
  getLatestScript,
  renderAudio,
  rerenderSegmentAudio,
} from "@/lib/api";
import type { AudioMix, Script, ScriptSegment } from "@/lib/types";
import { useJob } from "@/lib/useJob";
import { Badge, Button, Card, ErrorNote, ProgressBar } from "@/components/ui";

export default function AudioPage() {
  const { id } = useParams<{ id: string }>();
  const scriptSWR = useSWR<Script | null>(`script:${id}`, () =>
    getLatestScript(id).catch(() => null)
  );
  const audioSWR = useSWR<AudioMix | null>(`audio:${id}`, () =>
    getLatestAudio(id).catch(() => null)
  );
  const script = scriptSWR.data ?? null;
  const audio = audioSWR.data ?? null;
  const [err, setErr] = useState<string | null>(null);

  const blobSWR = useSWR<string | null>(
    audio ? `audioblob:${audio.mix_id}` : null,
    () => fetchBlobUrl((audio as AudioMix).download_url)
  );

  const job = useJob(() => {
    audioSWR.mutate();
    scriptSWR.mutate();
  });

  const highRisk = script?.safety_status === "high_risk";

  async function render() {
    setErr(null);
    try {
      const { job_id } = await renderAudio(id);
      job.start(job_id);
    } catch (e) {
      setErr(e instanceof ApiException ? e.message : "Could not start rendering.");
    }
  }

  async function download() {
    if (!audio) return;
    try {
      const url = await fetchBlobUrl(audio.download_url);
      const a = document.createElement("a");
      a.href = url;
      a.download = `episode_${id}.${audio.format}`;
      a.click();
    } catch (e) {
      setErr(e instanceof ApiException ? e.message : "Download failed.");
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-center justify-between">
          <Link
            href={`/episodes/${id}/script`}
            className="text-sm text-neutral-500 hover:text-neutral-900"
          >
            ← Script
          </Link>
          <Link
            href={`/episodes/${id}/export`}
            className="text-sm text-neutral-500 hover:text-neutral-900"
          >
            Export →
          </Link>
        </div>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight">Audio</h1>
      </div>

      {highRisk && (
        <ErrorNote message="This script is flagged high_risk by QA and cannot be rendered. Resolve the safety warnings and re-run QA first." />
      )}

      <Card className="flex flex-wrap items-center justify-between gap-3">
        <div className="text-sm text-neutral-600">
          {audio ? (
            <span className="flex items-center gap-2">
              Mix <Badge tone={audio.status === "stale" ? "amber" : "green"}>{audio.status}</Badge>
              {audio.duration_ms ? `· ${Math.round(audio.duration_ms / 1000)}s` : ""}
            </span>
          ) : (
            "No audio yet. Render the script into a multi-speaker mix."
          )}
        </div>
        <div className="flex items-center gap-2">
          {audio && (
            <Button variant="secondary" onClick={download}>
              Download {audio.format.toUpperCase()}
            </Button>
          )}
          <Button onClick={render} disabled={job.running || highRisk || !script}>
            {job.running ? "Rendering…" : audio ? "Re-render all" : "Render audio"}
          </Button>
        </div>
      </Card>

      {job.running && <ProgressBar value={job.job?.progress ?? 0} />}
      <ErrorNote message={err} />

      {audio && blobSWR.data && (
        <Card>
          {audio.status === "stale" && (
            <p className="mb-2 text-xs text-amber-700">
              The script changed since this mix was made — re-render for an up-to-date episode.
            </p>
          )}
          <audio controls src={blobSWR.data} className="w-full" />
        </Card>
      )}

      {script && (
        <section className="space-y-2">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-neutral-500">
            Segments
          </h2>
          {script.segments.map((seg) => (
            <SegmentAudioRow
              key={seg.id}
              segment={seg}
              disabled={highRisk}
              onDone={() => audioSWR.mutate()}
            />
          ))}
        </section>
      )}
    </div>
  );
}

function SegmentAudioRow({
  segment,
  disabled,
  onDone,
}: {
  segment: ScriptSegment;
  disabled: boolean;
  onDone: () => void;
}) {
  const job = useJob(() => onDone());
  const [err, setErr] = useState<string | null>(null);

  async function rerender() {
    setErr(null);
    try {
      const { job_id } = await rerenderSegmentAudio(segment.id);
      job.start(job_id);
    } catch (e) {
      setErr(e instanceof ApiException ? e.message : "Could not re-render.");
    }
  }

  return (
    <Card className="flex items-center justify-between gap-3 py-2">
      <div className="min-w-0">
        <Badge tone="blue">{segment.speaker_label}</Badge>{" "}
        <span className="text-sm text-neutral-600">
          {segment.text.length > 80 ? segment.text.slice(0, 80) + "…" : segment.text}
        </span>
        <ErrorNote message={err} />
      </div>
      <Button variant="ghost" onClick={rerender} disabled={job.running || disabled}>
        {job.running ? "…" : "Re-render"}
      </Button>
    </Card>
  );
}
