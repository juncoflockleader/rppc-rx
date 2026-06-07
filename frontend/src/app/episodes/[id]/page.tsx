"use client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import useSWR from "swr";
import {
  ApiException,
  fetcher,
  generatePlan,
  getPlan,
  getRoleContext,
} from "@/lib/api";
import type { DiscussionPlan, Episode, RoleContext } from "@/lib/types";
import { useJob } from "@/lib/useJob";
import {
  Badge,
  Button,
  Card,
  ErrorNote,
  ProgressBar,
  statusTone,
} from "@/components/ui";

export default function EpisodePage() {
  const { id } = useParams<{ id: string }>();
  const episode = useSWR<Episode>(`/api/episodes/${id}`, fetcher);
  // 404 (not generated yet) is a normal empty state, not an error.
  const planSWR = useSWR<DiscussionPlan | null>(`plan:${id}`, () =>
    getPlan(id).catch(() => null)
  );
  const rolesSWR = useSWR<RoleContext | null>(`roles:${id}`, () =>
    getRoleContext(id).catch(() => null)
  );
  const plan = planSWR.data ?? null;
  const roles = rolesSWR.data ?? null;
  const [err, setErr] = useState<string | null>(null);

  const { job, running, start } = useJob(() => {
    episode.mutate();
    planSWR.mutate();
    rolesSWR.mutate();
  });

  async function generate() {
    setErr(null);
    try {
      const { job_id } = await generatePlan(id);
      start(job_id);
    } catch (e) {
      setErr(e instanceof ApiException ? e.message : "Could not start planning.");
    }
  }

  const ep = episode.data;
  return (
    <div className="space-y-6">
      <div>
        {ep && (
          <Link
            href={`/projects/${ep.project_id}`}
            className="text-sm text-neutral-500 hover:text-neutral-900"
          >
            ← Project
          </Link>
        )}
        <div className="mt-1 flex items-center gap-3">
          <h1 className="text-2xl font-semibold tracking-tight">
            {ep?.title ?? "Episode"}
          </h1>
          {ep && <Badge tone={statusTone(ep.status)}>{ep.status}</Badge>}
        </div>
        {ep && (
          <div className="mt-1 flex flex-wrap items-center gap-2 text-sm text-neutral-500">
            <span>{Math.round(ep.target_duration_seconds / 60)} min</span>
            <span>·</span>
            {ep.participants.map((p) => (
              <Badge key={p.speaker_label} tone={p.role === "host" ? "blue" : "neutral"}>
                {p.speaker_label}
              </Badge>
            ))}
          </div>
        )}
      </div>

      <Card className="flex items-center justify-between">
        <div className="text-sm text-neutral-600">
          {plan
            ? `Discussion plan v${plan.version} ready — ${plan.plan.beats.length} beats.`
            : "Generate role context cards and a discussion plan from the source + personas."}
        </div>
        <Button onClick={generate} disabled={running}>
          {running ? "Planning…" : plan ? "Regenerate" : "Generate plan"}
        </Button>
      </Card>

      {running && job && (
        <div className="space-y-1">
          <ProgressBar value={job.progress} />
          <div className="text-xs text-neutral-500">
            {job.job_type} — {Math.round(job.progress * 100)}%
          </div>
        </div>
      )}
      {job?.status === "failed" && (
        <ErrorNote message={job.error?.message ?? "Planning failed."} />
      )}
      <ErrorNote message={err} />

      {roles && roles.cards.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-neutral-500">
            Role context
          </h2>
          <div className="grid gap-3 md:grid-cols-2">
            {roles.cards.map((c) => (
              <Card key={c.speaker_label} className="space-y-2">
                <div className="font-medium">{c.speaker_label}</div>
                {c.card.episode_position && (
                  <p className="text-sm text-neutral-700">{c.card.episode_position}</p>
                )}
                <CardList label="Concepts" items={c.card.relevant_persona_concepts} tone="blue" />
                <CardList label="Likely agreements" items={c.card.likely_agreements} />
                <CardList label="Likely tensions" items={c.card.likely_tensions} />
              </Card>
            ))}
          </div>
        </section>
      )}

      {plan && (
        <section className="space-y-3">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-neutral-500">
            Discussion plan
          </h2>
          {plan.plan.beats.map((b, i) => (
            <Card key={b.beat_id ?? i} className="space-y-1">
              <div className="flex items-center justify-between">
                <div className="font-medium">
                  <span className="text-neutral-400">{i + 1}.</span> {b.title}
                </div>
                <div className="flex items-center gap-2 text-xs text-neutral-500">
                  {b.primary_speaker && <Badge tone="blue">{b.primary_speaker}</Badge>}
                  <span>~{b.target_seconds}s</span>
                </div>
              </div>
              <p className="text-sm text-neutral-600">{b.goal}</p>
              {b.persona_concepts && b.persona_concepts.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {b.persona_concepts.map((c) => (
                    <Badge key={c}>{c}</Badge>
                  ))}
                </div>
              )}
            </Card>
          ))}
          {plan.plan.ending?.takeaway && (
            <Card className="bg-neutral-50">
              <div className="text-xs font-semibold uppercase tracking-wide text-neutral-500">
                Takeaway
              </div>
              <p className="text-sm text-neutral-700">{plan.plan.ending.takeaway}</p>
            </Card>
          )}
        </section>
      )}
    </div>
  );
}

function CardList({
  label,
  items,
  tone = "neutral",
}: {
  label: string;
  items?: string[];
  tone?: "neutral" | "blue";
}) {
  if (!items || items.length === 0) return null;
  return (
    <div>
      <div className="text-xs font-semibold uppercase tracking-wide text-neutral-400">
        {label}
      </div>
      {tone === "blue" ? (
        <div className="mt-1 flex flex-wrap gap-1">
          {items.map((t, i) => (
            <Badge key={i} tone="blue">
              {t}
            </Badge>
          ))}
        </div>
      ) : (
        <ul className="mt-0.5 space-y-0.5 text-sm text-neutral-700">
          {items.map((t, i) => (
            <li key={i}>· {t}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
