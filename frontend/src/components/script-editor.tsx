"use client";
import { useState } from "react";
import { ApiException, rewriteSegment, updateSegment } from "@/lib/api";
import type { QaPanel, QaWarning, ScriptSegment } from "@/lib/types";
import {
  Badge,
  Button,
  Card,
  ErrorNote,
  evidenceMeta,
  severityTone,
  statusTone,
} from "@/components/ui";

export function SegmentCard({
  segment,
  warnings,
  onChanged,
}: {
  segment: ScriptSegment;
  warnings: QaWarning[];
  onChanged: () => void;
}) {
  const [text, setText] = useState(segment.text);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [rewriting, setRewriting] = useState(false);
  const [instruction, setInstruction] = useState("");
  const dirty = text !== segment.text;

  async function save() {
    setBusy(true);
    setErr(null);
    try {
      await updateSegment(segment.id, text);
      onChanged();
    } catch (e) {
      setErr(e instanceof ApiException ? e.message : "Save failed.");
    } finally {
      setBusy(false);
    }
  }

  async function rewrite() {
    if (!instruction.trim()) return;
    setBusy(true);
    setErr(null);
    try {
      const res = await rewriteSegment(segment.id, instruction.trim());
      setText(res.text);
      setInstruction("");
      setRewriting(false);
      onChanged();
    } catch (e) {
      setErr(e instanceof ApiException ? e.message : "Rewrite failed.");
    } finally {
      setBusy(false);
    }
  }

  const needsReview = segment.status === "needs_review";
  return (
    <Card className={`space-y-2 ${needsReview ? "border-amber-300" : ""}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Badge tone="blue">{segment.speaker_label}</Badge>
          <span className="text-xs text-neutral-400">
            {segment.beat_id} · ~{segment.estimated_seconds}s
          </span>
        </div>
        <div className="flex items-center gap-1">
          {segment.evidence.map((e, i) => {
            const m = evidenceMeta(e.type);
            return (
              <Badge key={i} tone={m.tone}>
                {m.label}
                {e.concept ? `: ${e.concept}` : ""}
              </Badge>
            );
          })}
          {segment.status !== "draft" && (
            <Badge tone={statusTone(segment.status)}>{segment.status}</Badge>
          )}
        </div>
      </div>

      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        rows={2}
        className="w-full resize-y rounded-md border border-neutral-200 px-3 py-2 text-sm outline-none focus:border-neutral-900"
      />

      {warnings.length > 0 && (
        <ul className="space-y-1">
          {warnings.map((w, i) => (
            <li key={i} className="flex items-start gap-2 text-xs">
              <Badge tone={severityTone(w.severity)}>{w.severity}</Badge>
              <span className="text-neutral-600">
                {w.message}
                {w.suggested_action ? ` — ${w.suggested_action}` : ""}
              </span>
            </li>
          ))}
        </ul>
      )}

      <div className="flex items-center gap-2">
        <Button onClick={save} disabled={busy || !dirty}>
          {busy ? "Saving…" : "Save"}
        </Button>
        <Button variant="ghost" onClick={() => setRewriting((s) => !s)} disabled={busy}>
          Rewrite
        </Button>
        {dirty && (
          <Button variant="ghost" onClick={() => setText(segment.text)} disabled={busy}>
            Reset
          </Button>
        )}
      </div>

      {rewriting && (
        <div className="flex gap-2">
          <input
            value={instruction}
            onChange={(e) => setInstruction(e.target.value)}
            placeholder="e.g. make Laozi more concise"
            className="flex-1 rounded-md border border-neutral-300 px-3 py-1.5 text-sm outline-none focus:border-neutral-900"
          />
          <Button onClick={rewrite} disabled={busy || !instruction.trim()}>
            Apply
          </Button>
        </div>
      )}

      <ErrorNote message={err} />
    </Card>
  );
}

const SCORE_LABELS: Record<string, string> = {
  source_grounding_score: "Source grounding",
  persona_fidelity_score: "Persona fidelity",
  distinctiveness_score: "Distinctiveness",
  anachronism_score: "Anachronism",
  safety_score: "Safety",
  dialogue_quality_score: "Dialogue quality",
  audio_readiness_score: "Audio readiness",
};

export function QaPanelView({ qa }: { qa: QaPanel }) {
  const s = qa.summary;
  const safetyTone =
    qa.safety_status === "high_risk"
      ? "red"
      : qa.safety_status === "needs_review"
        ? "amber"
        : "green";
  return (
    <Card className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-neutral-500">
          QA report
        </h2>
        <div className="flex items-center gap-2 text-xs text-neutral-500">
          <span>Safety:</span>
          <Badge tone={safetyTone}>{qa.safety_status}</Badge>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-x-6 gap-y-2 sm:grid-cols-3">
        {Object.entries(SCORE_LABELS).map(([key, label]) => (
          <ScoreMeter key={key} label={label} value={s[key]} />
        ))}
      </div>

      <div className="flex gap-4 border-t border-neutral-100 pt-2 text-xs text-neutral-500">
        <span>
          High-severity:{" "}
          <strong className="text-neutral-800">
            {s.high_severity_warning_count ?? 0}
          </strong>
        </span>
        <span>
          Total warnings:{" "}
          <strong className="text-neutral-800">{s.total_warning_count ?? 0}</strong>
        </span>
        <span>
          Segments: <strong className="text-neutral-800">{s.total_segments ?? 0}</strong>
        </span>
      </div>
    </Card>
  );
}

function ScoreMeter({ label, value }: { label: string; value: number | null }) {
  const v = typeof value === "number" ? value : null;
  const pct = v === null ? 0 : Math.round(Math.max(0, Math.min(1, v)) * 100);
  const tone = v === null ? "bg-neutral-300" : pct >= 80 ? "bg-green-500" : pct >= 50 ? "bg-amber-500" : "bg-red-500";
  return (
    <div>
      <div className="flex items-center justify-between text-xs">
        <span className="text-neutral-500">{label}</span>
        <span className="text-neutral-700">{v === null ? "—" : `${pct}%`}</span>
      </div>
      <div className="mt-0.5 h-1.5 w-full overflow-hidden rounded-full bg-neutral-200">
        <div className={`h-full ${tone}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}
