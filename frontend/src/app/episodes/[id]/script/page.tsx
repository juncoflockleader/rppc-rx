"use client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import useSWR from "swr";
import {
  ApiException,
  fetcher,
  generateScript,
  getLatestScript,
  getQA,
  repairScript,
  runQA,
} from "@/lib/api";
import type { Episode, QaPanel, QaWarning, Script } from "@/lib/types";
import { useJob } from "@/lib/useJob";
import { Badge, Button, Card, ErrorNote, ProgressBar } from "@/components/ui";
import { QaPanelView, SegmentCard } from "@/components/script-editor";

export default function ScriptPage() {
  const { id } = useParams<{ id: string }>();
  const episode = useSWR<Episode>(`/api/episodes/${id}`, fetcher);
  const scriptSWR = useSWR<Script | null>(`script:${id}`, () =>
    getLatestScript(id).catch(() => null)
  );
  const script = scriptSWR.data ?? null;
  const vid = script?.script_version_id;
  const qaSWR = useSWR<QaPanel | null>(vid ? `qa:${vid}` : null, () =>
    getQA(vid as string).catch(() => null)
  );
  const qa = qaSWR.data ?? null;
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const scriptJob = useJob(() => {
    scriptSWR.mutate();
    episode.mutate();
  });
  const qaJob = useJob(() => {
    qaSWR.mutate();
    scriptSWR.mutate();
  });

  async function generate() {
    setErr(null);
    try {
      const { job_id } = await generateScript(id);
      scriptJob.start(job_id);
    } catch (e) {
      setErr(e instanceof ApiException ? e.message : "Could not start generation.");
    }
  }

  async function qaRun() {
    if (!vid) return;
    setErr(null);
    try {
      const { job_id } = await runQA(vid);
      qaJob.start(job_id);
    } catch (e) {
      setErr(e instanceof ApiException ? e.message : "Could not start QA.");
    }
  }

  async function repair() {
    if (!vid) return;
    setBusy(true);
    setErr(null);
    try {
      await repairScript(vid);
      scriptSWR.mutate();
      qaSWR.mutate();
    } catch (e) {
      setErr(e instanceof ApiException ? e.message : "Repair failed.");
    } finally {
      setBusy(false);
    }
  }

  // Map QA warnings to their segment.
  const warningsBySegment = new Map<string, QaWarning[]>();
  for (const r of qa?.reports ?? []) {
    for (const w of r.warnings) {
      if (!w.segment_id) continue;
      const arr = warningsBySegment.get(w.segment_id) ?? [];
      arr.push(w);
      warningsBySegment.set(w.segment_id, arr);
    }
  }
  const needsReview =
    script?.segments.filter((s) => s.status === "needs_review").length ?? 0;
  const share = script?.metadata?.speaker_share ?? {};

  return (
    <div className="space-y-6">
      <div>
        <Link
          href={`/episodes/${id}`}
          className="text-sm text-neutral-500 hover:text-neutral-900"
        >
          ← Outline
        </Link>
        <div className="mt-1 flex items-center justify-between">
          <h1 className="text-2xl font-semibold tracking-tight">
            Script {episode.data?.title ? `— ${episode.data.title}` : ""}
          </h1>
          {script && (
            <Link
              href={`/episodes/${id}/audio`}
              className="text-sm text-neutral-500 hover:text-neutral-900"
            >
              Audio &amp; export →
            </Link>
          )}
        </div>
      </div>

      <Card className="flex flex-wrap items-center justify-between gap-3">
        <div className="text-sm text-neutral-600">
          {script ? (
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
              <span>
                v{script.version} · {script.segments.length} segments ·{" "}
                ~{Math.round((script.total_estimated_seconds ?? 0) / 60)} min
              </span>
              {Object.entries(share).map(([label, frac]) => (
                <Badge key={label}>
                  {label} {Math.round((frac as number) * 100)}%
                </Badge>
              ))}
            </div>
          ) : (
            "No script yet. Generate one from the discussion plan."
          )}
        </div>
        <div className="flex items-center gap-2">
          {script && (
            <>
              <Button variant="secondary" onClick={qaRun} disabled={qaJob.running}>
                {qaJob.running ? "Running QA…" : "Run QA"}
              </Button>
              {needsReview > 0 && (
                <Button variant="secondary" onClick={repair} disabled={busy}>
                  {busy ? "Repairing…" : `Repair (${needsReview})`}
                </Button>
              )}
            </>
          )}
          <Button onClick={generate} disabled={scriptJob.running}>
            {scriptJob.running
              ? "Generating…"
              : script
                ? "Regenerate"
                : "Generate script"}
          </Button>
        </div>
      </Card>

      {(scriptJob.running || qaJob.running) && (
        <ProgressBar
          value={(scriptJob.running ? scriptJob.job : qaJob.job)?.progress ?? 0}
        />
      )}
      <ErrorNote message={err} />

      {qa && <QaPanelView qa={qa} />}

      {script && (
        <section className="space-y-3">
          {script.segments.map((seg) => (
            <SegmentCard
              key={seg.id}
              segment={seg}
              warnings={warningsBySegment.get(seg.id) ?? []}
              onChanged={() => scriptSWR.mutate()}
            />
          ))}
        </section>
      )}
    </div>
  );
}
