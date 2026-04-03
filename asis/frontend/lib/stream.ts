/**
 * SSE streaming client for the ASIS analysis pipeline.
 * Connects to POST /api/v1/analysis and dispatches typed events.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export type AgentEventType =
  | "agent_start"
  | "agent_complete"
  | "agent_error"
  | "analysis_complete"
  | "error";

export interface AgentStartEvent {
  agent: string;
}

export interface AgentCompleteEvent {
  agent: string;
  duration_ms: number;
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

export interface ErrorEvent {
  analysis_id?: string;
  message: string;
}

export type SSEEvent =
  | { type: "agent_start"; data: AgentStartEvent }
  | { type: "agent_complete"; data: AgentCompleteEvent }
  | { type: "agent_error"; data: AgentErrorEvent }
  | { type: "analysis_complete"; data: AnalysisCompleteEvent }
  | { type: "error"; data: ErrorEvent };

export type SSEEventHandler = (event: SSEEvent) => void;

/**
 * Trigger the ASIS pipeline and stream SSE events via fetch + ReadableStream.
 * Returns a cleanup function that aborts the request.
 */
export function streamAnalysis(
  request: {
    query: string;
    company_context: unknown;
    options?: unknown;
  },
  token: string,
  onEvent: SSEEventHandler,
  onDone: () => void,
  onError: (err: Error) => void
): () => void {
  const controller = new AbortController();

  (async () => {
    try {
      const res = await fetch(`${API_BASE}/analysis`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
          Accept: "text/event-stream",
        },
        body: JSON.stringify(request),
        signal: controller.signal,
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body?.detail ?? `HTTP ${res.status}`);
      }

      if (!res.body) throw new Error("No response body");

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // Parse SSE chunks: each event is "event: TYPE\ndata: JSON\n\n"
        const chunks = buffer.split("\n\n");
        buffer = chunks.pop() ?? "";

        for (const chunk of chunks) {
          const eventLine = chunk.match(/^event:\s*(.+)$/m)?.[1]?.trim();
          const dataLine = chunk.match(/^data:\s*(.+)$/m)?.[1]?.trim();

          if (eventLine && dataLine) {
            try {
              const data = JSON.parse(dataLine);
              onEvent({ type: eventLine as AgentEventType, data } as SSEEvent);
            } catch {
              // malformed JSON — ignore
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
