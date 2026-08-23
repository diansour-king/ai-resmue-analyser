"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { api } from "@/lib/api";
import type { Resume } from "@/lib/types";

const IN_FLIGHT = new Set(["uploaded", "queued", "processing"]);
const POLL_MS = 2000;

/**
 * Load a resume and keep polling while the backend says it is still working.
 *
 * The UI shows the state the backend actually reports. There is no percentage, because the
 * worker cannot produce one honestly: rendering and OCR do not report progress, and a bar
 * that invents its own position is a lie about how far along the work is.
 */
export function useResume(resumeId: string) {
  const [resume, setResume] = useState<Resume | null>(null);
  const [error, setError] = useState<unknown>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const load = useCallback(async () => {
    try {
      const next = await api.getResume(resumeId);
      setResume(next);
      setError(null);
      return next;
    } catch (caught) {
      setError(caught);
      return null;
    }
  }, [resumeId]);

  useEffect(() => {
    let cancelled = false;

    async function tick() {
      const next = await load();
      if (cancelled) return;
      if (next && IN_FLIGHT.has(next.state)) {
        timer.current = setTimeout(tick, POLL_MS);
      }
    }

    void tick();
    return () => {
      cancelled = true;
      if (timer.current) clearTimeout(timer.current);
    };
  }, [load]);

  return { resume, error, reload: load, isWorking: resume ? IN_FLIGHT.has(resume.state) : false };
}
