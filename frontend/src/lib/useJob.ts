"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { getJob } from "./api";
import type { Job } from "./types";

const TERMINAL = new Set(["completed", "failed", "canceled"]);

// Polls a job to completion. Call start(jobId); read {job, running}.
// onDone fires once when the job reaches a terminal state.
export function useJob(onDone?: (job: Job) => void) {
  const [jobId, setJobId] = useState<string | null>(null);
  const [job, setJob] = useState<Job | null>(null);
  const onDoneRef = useRef(onDone);
  useEffect(() => {
    onDoneRef.current = onDone;
  }, [onDone]);

  useEffect(() => {
    if (!jobId) return;
    let active = true;
    let timer: ReturnType<typeof setTimeout> | undefined;

    const tick = async () => {
      if (!active) return;
      try {
        const j = await getJob(jobId);
        if (!active) return;
        setJob(j);
        if (TERMINAL.has(j.status)) {
          onDoneRef.current?.(j);
          setJobId(null);
          return;
        }
      } catch {
        // transient; keep polling
      }
      timer = setTimeout(tick, 500);
    };
    tick();

    return () => {
      active = false;
      if (timer) clearTimeout(timer);
    };
  }, [jobId]);

  const start = useCallback((id: string) => {
    setJob(null);
    setJobId(id);
  }, []);

  return { job, running: jobId !== null, start };
}
