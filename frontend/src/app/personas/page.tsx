"use client";
import { useState } from "react";
import useSWR from "swr";
import { fetcher, getPersonaVersion } from "@/lib/api";
import type { PersonaCard, PersonaVersion } from "@/lib/types";
import { Badge, Card, ErrorNote, statusTone } from "@/components/ui";

export default function PersonasPage() {
  const { data, error, isLoading } = useSWR<PersonaCard[]>(
    "/api/personas",
    fetcher
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Personas</h1>
        <p className="text-sm text-neutral-500">
          Versioned, interpretive persona assets. Each carries its own knowledge
          boundary, stance, voice, and forbidden moves.
        </p>
      </div>

      {error && (
        <ErrorNote message="Could not load personas. Has the library been seeded (make seed-personas)?" />
      )}
      {isLoading && <p className="text-sm text-neutral-500">Loading…</p>}

      <div className="grid gap-3">
        {data?.map((p) => (
          <PersonaItem key={`${p.persona_id}@${p.version}`} card={p} />
        ))}
        {data?.length === 0 && (
          <p className="text-sm text-neutral-500">
            No personas seeded yet.
          </p>
        )}
      </div>
    </div>
  );
}

function PersonaItem({ card }: { card: PersonaCard }) {
  const [open, setOpen] = useState(false);
  const [detail, setDetail] = useState<PersonaVersion | null>(null);
  const [loading, setLoading] = useState(false);

  async function toggle() {
    const next = !open;
    setOpen(next);
    if (next && !detail) {
      setLoading(true);
      try {
        setDetail(await getPersonaVersion(card.persona_id, card.version));
      } finally {
        setLoading(false);
      }
    }
  }

  return (
    <Card className="space-y-3">
      <button onClick={toggle} className="flex w-full items-start justify-between text-left">
        <div>
          <div className="font-medium">
            {card.display_name ?? card.persona_id}{" "}
            <span className="text-xs text-neutral-400">{card.version}</span>
          </div>
          {card.summary && (
            <p className="mt-0.5 max-w-2xl text-sm text-neutral-600">{card.summary}</p>
          )}
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {card.type && <Badge>{card.type.replace(/_/g, " ")}</Badge>}
          {card.status && <Badge tone={statusTone(card.status)}>{card.status}</Badge>}
        </div>
      </button>

      {open && (
        <div className="border-t border-neutral-100 pt-3">
          {loading && <p className="text-sm text-neutral-500">Loading…</p>}
          {detail && <PersonaDetail v={detail} />}
        </div>
      )}
    </Card>
  );
}

function PersonaDetail({ v }: { v: PersonaVersion }) {
  const stance = v.stance_matrix ?? {};
  return (
    <div className="space-y-4 text-sm">
      {v.identity_profile?.disclaimer && (
        <p className="rounded-md bg-amber-50 px-3 py-2 text-xs text-amber-800">
          {v.identity_profile.disclaimer}
        </p>
      )}

      {Object.keys(stance).length > 0 && (
        <div>
          <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-neutral-500">
            Stance
          </h3>
          <dl className="grid gap-1">
            {Object.entries(stance).map(([k, val]) => (
              <div key={k} className="grid grid-cols-[8rem_1fr] gap-2">
                <dt className="text-neutral-500">{k}</dt>
                <dd className="text-neutral-700">
                  {(val as { position?: string })?.position ?? JSON.stringify(val)}
                </dd>
              </div>
            ))}
          </dl>
        </div>
      )}

      {v.forbidden_moves && v.forbidden_moves.length > 0 && (
        <div>
          <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-neutral-500">
            Forbidden moves
          </h3>
          <ul className="space-y-0.5 text-neutral-700">
            {v.forbidden_moves.map((m, i) => (
              <li key={i}>
                <span className="text-red-400">✕</span> {m}
              </li>
            ))}
          </ul>
        </div>
      )}

      {v.release_notes && (
        <p className="text-xs text-neutral-500">{v.release_notes}</p>
      )}
    </div>
  );
}
