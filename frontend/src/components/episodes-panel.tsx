"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import useSWR from "swr";
import { ApiException, createEpisode, fetcher } from "@/lib/api";
import type { Episode, EpisodeParticipant, PersonaCard } from "@/lib/types";
import { Badge, Button, Card, ErrorNote, statusTone } from "@/components/ui";

function speakerLabel(personaId: string) {
  return personaId === "modern_host" ? "HOST" : personaId.toUpperCase();
}

export function EpisodesPanel({ projectId }: { projectId: string }) {
  const episodes = useSWR<Episode[]>(
    `/api/projects/${projectId}/episodes`,
    fetcher
  );
  const [showForm, setShowForm] = useState(false);

  return (
    <section className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-neutral-500">
          Episodes
        </h2>
        <Button variant="secondary" onClick={() => setShowForm((s) => !s)}>
          {showForm ? "Cancel" : "New episode"}
        </Button>
      </div>

      {showForm && (
        <NewEpisodeForm
          projectId={projectId}
          onCreated={() => {
            setShowForm(false);
            episodes.mutate();
          }}
        />
      )}

      {episodes.data?.length === 0 && !showForm && (
        <p className="text-sm text-neutral-500">
          No episodes yet. Create one to pick personas and plan the discussion.
        </p>
      )}
      {episodes.data?.map((e) => (
        <Link key={e.id} href={`/episodes/${e.id}`}>
          <Card className="flex items-center justify-between hover:border-neutral-400">
            <div>
              <div className="font-medium">{e.title ?? "Untitled episode"}</div>
              <div className="text-xs text-neutral-500">
                {Math.round(e.target_duration_seconds / 60)} min · {e.format}
              </div>
            </div>
            <Badge tone={statusTone(e.status)}>{e.status}</Badge>
          </Card>
        </Link>
      ))}
    </section>
  );
}

function NewEpisodeForm({
  projectId,
  onCreated,
}: {
  projectId: string;
  onCreated: () => void;
}) {
  const router = useRouter();
  const { data: personas } = useSWR<PersonaCard[]>("/api/personas", fetcher);

  const hosts = useMemo(
    () => (personas ?? []).filter((p) => p.persona_id === "modern_host"),
    [personas]
  );
  const guests = useMemo(
    () => (personas ?? []).filter((p) => p.persona_id !== "modern_host"),
    [personas]
  );

  const [title, setTitle] = useState("");
  const [goal, setGoal] = useState("");
  const [minutes, setMinutes] = useState(10);
  const [hostId, setHostId] = useState("modern_host");
  const [picked, setPicked] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  function toggleGuest(id: string) {
    setPicked((cur) =>
      cur.includes(id) ? cur.filter((x) => x !== id) : cur.length < 2 ? [...cur, id] : cur
    );
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (picked.length < 1) {
      setErr("Pick one or two guests.");
      return;
    }
    setBusy(true);
    setErr(null);
    try {
      const byId = new Map((personas ?? []).map((p) => [p.persona_id, p]));
      const host = byId.get(hostId);
      const participants: EpisodeParticipant[] = [
        {
          persona_id: hostId,
          version: host?.version ?? "v1.0",
          role: "host",
          speaker_label: "HOST",
        },
        ...picked.map((id) => ({
          persona_id: id,
          version: byId.get(id)?.version ?? "v1.0",
          role: "guest",
          speaker_label: speakerLabel(id),
        })),
      ];
      const ep = await createEpisode(projectId, {
        title: title.trim() || undefined,
        goal: goal.trim() || undefined,
        target_duration_seconds: minutes * 60,
        personas: participants,
      });
      onCreated();
      router.push(`/episodes/${ep.id}`);
    } catch (e) {
      setErr(e instanceof ApiException ? e.message : "Could not create episode.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <form onSubmit={submit} className="space-y-3">
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Episode title"
          className="w-full rounded-md border border-neutral-300 px-3 py-1.5 text-sm outline-none focus:border-neutral-900"
        />
        <input
          value={goal}
          onChange={(e) => setGoal(e.target.value)}
          placeholder="Goal — e.g. Help listeners understand desire"
          className="w-full rounded-md border border-neutral-300 px-3 py-1.5 text-sm outline-none focus:border-neutral-900"
        />

        <div className="flex flex-wrap items-center gap-4 text-sm">
          <label className="flex items-center gap-2">
            <span className="text-neutral-500">Host</span>
            <select
              value={hostId}
              onChange={(e) => setHostId(e.target.value)}
              className="rounded-md border border-neutral-300 px-2 py-1"
            >
              {hosts.map((h) => (
                <option key={h.persona_id} value={h.persona_id}>
                  {h.display_name ?? h.persona_id}
                </option>
              ))}
            </select>
          </label>
          <label className="flex items-center gap-2">
            <span className="text-neutral-500">Length</span>
            <select
              value={minutes}
              onChange={(e) => setMinutes(Number(e.target.value))}
              className="rounded-md border border-neutral-300 px-2 py-1"
            >
              {[3, 8, 10, 15].map((m) => (
                <option key={m} value={m}>
                  {m} min
                </option>
              ))}
            </select>
          </label>
        </div>

        <div>
          <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-neutral-500">
            Guests (1–2)
          </div>
          <div className="flex flex-wrap gap-2">
            {guests.map((g) => {
              const on = picked.includes(g.persona_id);
              return (
                <button
                  type="button"
                  key={g.persona_id}
                  onClick={() => toggleGuest(g.persona_id)}
                  className={`rounded-full border px-3 py-1 text-sm transition ${
                    on
                      ? "border-neutral-900 bg-neutral-900 text-white"
                      : "border-neutral-300 hover:bg-neutral-100"
                  }`}
                >
                  {g.display_name ?? g.persona_id}
                </button>
              );
            })}
          </div>
        </div>

        <ErrorNote message={err} />
        <Button type="submit" disabled={busy || picked.length < 1}>
          {busy ? "Creating…" : "Create episode"}
        </Button>
      </form>
    </Card>
  );
}
