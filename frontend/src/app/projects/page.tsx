"use client";
import Link from "next/link";
import { useState } from "react";
import useSWR from "swr";
import { ApiException, createProject, fetcher } from "@/lib/api";
import type { Project } from "@/lib/types";
import { Badge, Button, Card, ErrorNote, statusTone } from "@/components/ui";

export default function ProjectsPage() {
  const { data, error, isLoading, mutate } = useSWR<Project[]>(
    "/api/projects",
    fetcher
  );
  const [title, setTitle] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim()) return;
    setBusy(true);
    setErr(null);
    try {
      await createProject({ title: title.trim() });
      setTitle("");
      mutate();
    } catch (e) {
      setErr(e instanceof ApiException ? e.message : "Failed to create project.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Projects</h1>
        <p className="text-sm text-neutral-500">
          A project holds your source material, chosen personas, and generated
          episodes.
        </p>
      </div>

      <Card>
        <form onSubmit={create} className="flex gap-2">
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="New project title…"
            className="flex-1 rounded-md border border-neutral-300 px-3 py-1.5 text-sm outline-none focus:border-neutral-900"
          />
          <Button type="submit" disabled={busy || !title.trim()}>
            {busy ? "Creating…" : "Create"}
          </Button>
        </form>
        <div className="mt-2">
          <ErrorNote message={err} />
        </div>
      </Card>

      {error && <ErrorNote message="Could not load projects. Is the backend running?" />}
      {isLoading && <p className="text-sm text-neutral-500">Loading…</p>}

      <div className="grid gap-3">
        {data?.map((p) => (
          <Link key={p.id} href={`/projects/${p.id}`}>
            <Card className="flex items-center justify-between hover:border-neutral-400">
              <div>
                <div className="font-medium">{p.title}</div>
                <div className="text-xs text-neutral-500">{p.id}</div>
              </div>
              <Badge tone={statusTone(p.status)}>{p.status}</Badge>
            </Card>
          </Link>
        ))}
        {data?.length === 0 && (
          <p className="text-sm text-neutral-500">No projects yet.</p>
        )}
      </div>
    </div>
  );
}
