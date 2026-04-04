/**
 * SSE streaming client for the ASIS v3.0 analysis pipeline.
 *
 * Uses fetch + ReadableStream (not native EventSource) so we can send
 * auth headers. Includes automatic reconnect on network failure.
 */

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

const MAX_RECONNECT_ATTEMPTS = 3;
const RECONNECT_DELAY_MS = 1500;

// ── Event types ───────────────────────────────────────────────────────────────

export type AgentEventType =
  | "agent_start"
  | "agent_progress"
  | "agent_complete"
  | "agent_error"
  | "analysis_complete"
  | "error";

export interface AgentStartEvent {
  agent: string;
}

export interface AgentProgressEvent {
  agent: string;
  progress: number;
  tokens_so_far?: number;
}

export interface AgentCompleteEvent {
  agent: string;
  duration_ms: number;
  tokens_used?: number;
  rag_hits?: number;
  memory_hit?: boolean;
}

export interface AgentErrorEvent {
  agent: string;
  error: string;
}

export interface AnalysisCompleteEvent {
  analysis_id: string;
  duration_ms: number;
  strategic_brief: unknown;
  errors: string[];
}

export interface StreamErrorEvent {
  analysis_id?: string;
  message: string;
}

export type SSEEvent =
  | { type: "agent_start"; data: AgentStartEvent }
  | { type: "agent_progress"; data: AgentProgressEvent }
  | { type: "agent_complete"; data: AgentCompleteEvent }
  | { type: "agent_error"; data: AgentErrorEvent }
  | { type: "analysis_complete"; data: AnalysisCompleteEvent }
  | { type: "error"; data: StreamErrorEvent };

export type SSEEventHandler = (event: SSEEvent) => void;

interface StreamRequest {
  query: string;
  company_context: unknown;
  options?: unknown;
}

// ── Core stream function ──────────────────────────────────────────────────────

/**
 * Opens a POST SSE connection to /v1/analysis and dispatches typed events.
 * Returns an abort function.
 */
export function streamAnalysis(
  request: StreamRequest,
  token: string,
  onEvent: SSEEventHandler,
  onDone: () => void,
  onError: (err: Error) => void,
  options: { reconnect?: boolean } = {}
): () => void {
  const controller = new AbortController();
  const { reconnect = true } = options;

  let attempt = 0;

  const run = async (): Promise<void> => {
    try {
      const res = await fetch(`${API_BASE}/analysis`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
          Accept: "text/event-stream",
          "Cache-Control": "no-cache",
        },
        body: JSON.stringify(request),
        signal: controller.signal,
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({})) as { detail?: string };
        throw new Error(body?.detail ?? `HTTP ${res.status}`);
      }

      if (!res.body) throw new Error("No response body");

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      // Reset reconnect counter on successful connection
      attempt = 0;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // SSE format: each event is separated by "\n\n"
        const chunks = buffer.split("\n\n");
        buffer = chunks.pop() ?? "";

        for (const chunk of chunks) {
          if (!chunk.trim()) continue;

          const eventLine = chunk.match(/^event:\s*(.+)$/m)?.[1]?.trim();
          const dataLine = chunk.match(/^data:\s*(.+)$/m)?.[1]?.trim();

          if (eventLine && dataLine) {
            try {
              const parsed: unknown = JSON.parse(dataLine);
              onEvent({
                type: eventLine as AgentEventType,
                data: parsed,
              } as SSEEvent);
            } catch {
              // Malformed JSON — skip silently
            }
          }
        }
      }

      onDone();
    } catch (err) {
      if ((err as Error)?.name === "AbortError") {
        // User-initiated abort — don't reconnect
        return;
      }

      attempt += 1;

      if (reconnect && attempt <= MAX_RECONNECT_ATTEMPTS) {
        await sleep(RECONNECT_DELAY_MS * attempt);
        if (!controller.signal.aborted) {
          return run();
        }
      } else {
        onError(err instanceof Error ? err : new Error(String(err)));
      }
    }
  };

  run();

  return () => controller.abort();
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// ── Standalone SSE listener (for existing analysis) ───────────────────────────

/**
 * Subscribes to SSE events for an already-running analysis by ID.
 * Uses GET /v1/analysis/:id/stream
 */
export function subscribeToAnalysis(
  analysisId: string,
  token: string,
  onEvent: SSEEventHandler,
  onDone: () => void,
  onError: (err: Error) => void
): () => void {
  const controller = new AbortController();

  (async () => {
    try {
      const res = await fetch(`${API_BASE}/analysis/${analysisId}/stream`, {
        headers: {
          Authorization: `Bearer ${token}`,
          Accept: "text/event-stream",
          "Cache-Control": "no-cache",
        },
        signal: controller.signal,
      });

      if (!res.ok || !res.body) {
        throw new Error(`HTTP ${res.status}`);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const chunks = buffer.split("\n\n");
        buffer = chunks.pop() ?? "";

        for (const chunk of chunks) {
          if (!chunk.trim()) continue;
          const eventLine = chunk.match(/^event:\s*(.+)$/m)?.[1]?.trim();
          const dataLine = chunk.match(/^data:\s*(.+)$/m)?.[1]?.trim();
          if (eventLine && dataLine) {
            try {
              const parsed: unknown = JSON.parse(dataLine);
              onEvent({ type: eventLine as AgentEventType, data: parsed } as SSEEvent);
            } catch {
              // ignore
            }
          }
        }
      }

      onDone();
    } catch (err) {
      if ((err as Error)?.name !== "AbortError") {
        onError(err instanceof Error ? err : new Error(String(err)));
      }
    }
  })();

  return () => controller.abort();
}
