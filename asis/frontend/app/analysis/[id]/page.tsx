"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { slideUp, fadeIn } from "@/lib/animations";
import { getAnalysis, getToken, type AnalysisDetail, type StrategicBrief } from "@/lib/api";
import { AgentTimeline } from "@/components/AgentTimeline";
import { StrategyBrief } from "@/components/StrategyBrief";
import { StatusBadge } from "@/components/ui/Badge";
import { ArrowLeft, Terminal, ChevronDown, ChevronUp } from "lucide-react";

interface LogEntry {
  ts: number;
  message: string;
  level: "info" | "error" | "success";
  agent?: string;
}

const AGENT_COLORS: Record<string, string> = {
  orchestrator: "#7c3aed",
  market_intelligence: "#0ea5e9",
  risk_assessment: "#ef4444",
  financial_reasoning: "#10b981",
  competitor_analysis: "#f59e0b",
  synthesis: "#8b5cf6",
};

export default function AnalysisDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [detail, setDetail] = useState<AnalysisDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [timelineCollapsed, setTimelineCollapsed] = useState(false);
  const logsEndRef = useRef<HTMLDivElement>(null);
  const sseRef = useRef<EventSource | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const addLog = useCallback((message: string, level: LogEntry["level"] = "info", agent?: string) => {
    setLogs((prev) => [...prev, { ts: Date.now(), message, level, agent }]);
  }, []);

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  // Collapse timeline once report is ready so user can focus on brief
  useEffect(() => {
    if (detail?.status === "completed" && detail.strategic_brief) {
      // Slight delay so the transition feels intentional
      const t = setTimeout(() => setTimelineCollapsed(true), 800);
      return () => clearTimeout(t);
    }
  }, [detail?.status, detail?.strategic_brief]);

  useEffect(() => {
    if (!id) return;

    const apiBase = process.env.NEXT_PUBLIC_API_URL ?? "";

    addLog(`Loading analysis ${id}…`);

    // Initial load
    getAnalysis(id)
      .then((d) => {
        setDetail(d);
        addLog(`Status: ${d.status}`, d.status === "failed" ? "error" : "info");
        if (d.status === "completed" && d.strategic_brief) {
          addLog("Strategic brief ready.", "success");
        }
      })
      .catch((e: Error) => {
        setError(e.message);
        addLog(`Error: ${e.message}`, "error");
      })
      .finally(() => setLoading(false));

    // Try SSE stream for live agent events.
    // EventSource cannot send custom headers — pass JWT as ?token= query param.
    const jwt = getToken();
    const streamUrl = `${apiBase}/analysis/${id}/stream${jwt ? `?token=${encodeURIComponent(jwt)}` : ""}`;
    try {
      const es = new EventSource(streamUrl, { withCredentials: true });
      sseRef.current = es;

      es.addEventListener("agent_log", (e: MessageEvent) => {
        try {
          const data = JSON.parse(e.data) as {
            agent: string;
            level: string;
            message: string;
          };
          addLog(data.message, data.level === "error" ? "error" : data.level === "success" ? "success" : "info", data.agent);
        } catch {
          // ignore parse errors
        }
      });

      es.addEventListener("agent_start", (e: MessageEvent) => {
        try {
          const data = JSON.parse(e.data) as { agent: string };
          addLog(`[${data.agent}] starting…`, "info", data.agent);
        } catch { /* */ }
      });

      es.addEventListener("agent_complete", (e: MessageEvent) => {
        try {
          const data = JSON.parse(e.data) as { agent: string; duration_ms: number; tokens: number };
          addLog(`[${data.agent}] complete — ${data.tokens}t · ${data.duration_ms}ms`, "success", data.agent);
        } catch { /* */ }
      });

      es.addEventListener("agent_error", (e: MessageEvent) => {
        try {
          const data = JSON.parse(e.data) as { agent: string; error: string };
          addLog(`[${data.agent}] error: ${data.error}`, "error", data.agent);
        } catch { /* */ }
      });

      es.addEventListener("analysis_complete", () => {
        addLog("Pipeline complete — loading strategic brief…", "success");
        es.close();
        // Fetch final detail with strategic_brief — retry up to 3× in case
        // the DB write hasn't committed yet when the SSE event fires.
        const fetchWithRetry = (retries: number) => {
          getAnalysis(id)
            .then((d) => {
              setDetail(d);
              if (!d.strategic_brief && retries > 0) {
                setTimeout(() => fetchWithRetry(retries - 1), 1500);
              }
            })
            .catch(() => {
              if (retries > 0) setTimeout(() => fetchWithRetry(retries - 1), 1500);
            });
        };
        fetchWithRetry(3);
      });

      es.addEventListener("error", () => {
        // SSE failed — fall back to polling
        es.close();
        startPolling();
      });
    } catch {
      startPolling();
    }

    function startPolling() {
      if (pollRef.current) return; // already polling
      pollRef.current = setInterval(async () => {
        const d = await getAnalysis(id).catch(() => null);
        if (!d) return;
        setDetail(d);
        if (d.status === "completed") {
          addLog("Pipeline complete.", "success");
          clearInterval(pollRef.current!);
          pollRef.current = null;
        } else if (d.status === "failed") {
          addLog("Pipeline failed.", "error");
          clearInterval(pollRef.current!);
          pollRef.current = null;
        } else {
          const running = d.agent_runs.find((r) => r.status === "running");
          if (running) addLog(`[${running.agent_name}] running…`, "info", running.agent_name);
        }
      }, 3000);
    }

    return () => {
      sseRef.current?.close();
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [id, addLog]);

  if (loading) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: "60vh", flexDirection: "column", gap: 12 }}>
        <div style={{ width: 32, height: 32, borderRadius: "50%", border: "3px solid var(--border)", borderTopColor: "var(--accent)", animation: "spin 0.8s linear infinite" }} />
        <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>Loading analysis…</p>
      </div>
    );
  }

  if (error || !detail) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: "60vh", flexDirection: "column", gap: 16 }}>
        <p style={{ fontSize: 14, color: "var(--danger)" }}>{error ?? "Analysis not found"}</p>
        <Link href="/" style={{ fontSize: 13, color: "var(--accent)", textDecoration: "none", display: "flex", alignItems: "center", gap: 6 }}>
          <ArrowLeft size={14} />Back to dashboard
        </Link>
      </div>
    );
  }

  const isComplete = detail.status === "completed" && detail.strategic_brief != null;
  const isCompletedNoBrief = detail.status === "completed" && detail.strategic_brief == null;

  return (
    <div style={{ padding: "28px 28px 80px", maxWidth: 1400, margin: "0 auto" }}>
      {/* Page header */}
      <div style={{ marginBottom: 24 }}>
        <Link
          href="/"
          style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: 12, color: "var(--text-tertiary)", textDecoration: "none", marginBottom: 12 }}
          onMouseEnter={(e) => { (e.currentTarget as HTMLAnchorElement).style.color = "var(--text-secondary)"; }}
          onMouseLeave={(e) => { (e.currentTarget as HTMLAnchorElement).style.color = "var(--text-tertiary)"; }}
        >
          <ArrowLeft size={12} />Dashboard
        </Link>

        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 16 }}>
          <div>
            <h1 style={{ fontSize: 20, fontWeight: 700, color: "var(--text-primary)", letterSpacing: "-0.02em", lineHeight: 1.3, marginBottom: 6 }}>
              {detail.query}
            </h1>
            <p style={{ fontSize: 12, color: "var(--text-tertiary)" }}>
              {detail.company_context.company_name} · {detail.company_context.sector} · {detail.company_context.target_market}
            </p>
          </div>
          <StatusBadge status={detail.status} />
        </div>
      </div>

      {/* ── Completed but no brief: surface clearly instead of stuck pipeline ── */}
      {isCompletedNoBrief && (
        <div style={{ padding: "32px 24px", borderRadius: "var(--radius-lg)", border: "1px solid var(--border)", backgroundColor: "var(--bg-surface)", textAlign: "center", marginBottom: 20 }}>
          <p style={{ fontSize: 14, color: "var(--warning)", fontWeight: 600, marginBottom: 8 }}>
            Pipeline completed but strategic brief is unavailable
          </p>
          <p style={{ fontSize: 12, color: "var(--text-tertiary)", marginBottom: 16 }}>
            The agents ran successfully but the brief could not be retrieved. This is a known issue being fixed.
            Try running a new analysis — the fix is live on new submissions.
          </p>
          <Link href="/analysis/new" style={{ display: "inline-flex", alignItems: "center", gap: 6, padding: "8px 16px", backgroundColor: "var(--accent)", color: "white", borderRadius: "var(--radius-md)", fontSize: 13, fontWeight: 500, textDecoration: "none" }}>
            New Analysis
          </Link>
        </div>
      )}

      {/* ── Phase 1: Running — two-column: timeline left, log right ── */}
      <AnimatePresence mode="wait">
        {!isComplete ? (
          <motion.div
            key="pipeline-view"
            initial={fadeIn.initial}
            animate={fadeIn.animate}
            exit={{ opacity: 0, transition: { duration: 0.3 } }}
            transition={fadeIn.transition}
            style={{ display: "grid", gridTemplateColumns: "3fr 2fr", gap: 20, alignItems: "flex-start" }}
          >
            {/* AgentTimeline */}
            <div>
              <AgentTimeline agentRuns={detail.agent_runs} status={detail.status} executionTimeMs={detail.execution_time_ms} />
              {detail.status === "running" && (
                <div style={{ marginTop: 12, padding: "10px 14px", backgroundColor: "var(--accent-dim)", borderRadius: "var(--radius-md)", border: "1px solid rgba(124,58,237,0.25)", display: "flex", alignItems: "center", gap: 8, fontSize: 12, color: "var(--accent)" }}>
                  <div style={{ width: 10, height: 10, borderRadius: "50%", border: "2px solid transparent", borderTopColor: "var(--accent)", animation: "spin 0.7s linear infinite", flexShrink: 0 }} />
                  ASIS agents are working… typically 2–4 minutes
                </div>
              )}
            </div>

            {/* Log panel */}
            <LogPanel logs={logs} logsEndRef={logsEndRef} />
          </motion.div>
        ) : (
          /* ── Phase 2: Complete — full-width strategic brief ── */
          <motion.div
            key="complete-view"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
          >
            {/* Collapsible agent timeline summary */}
            <div style={{ marginBottom: 20 }}>
              <button
                onClick={() => setTimelineCollapsed((c) => !c)}
                style={{ display: "flex", alignItems: "center", gap: 8, background: "none", border: "1px solid var(--border)", borderRadius: "var(--radius-md)", padding: "8px 14px", cursor: "pointer", color: "var(--text-secondary)", fontSize: 12, fontWeight: 500, width: "100%", justifyContent: "space-between" }}
              >
                <span>Pipeline Summary — {(detail.agent_runs ?? []).filter((r) => r.status === "completed").length}/{(detail.agent_runs ?? []).length} agents · {detail.execution_time_ms ? `${(detail.execution_time_ms / 1000).toFixed(1)}s` : "—"}</span>
                {timelineCollapsed ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
              </button>
              <AnimatePresence>
                {!timelineCollapsed && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.25 }}
                    style={{ overflow: "hidden" }}
                  >
                    <div style={{ paddingTop: 12 }}>
                      <AgentTimeline agentRuns={detail.agent_runs} status={detail.status} executionTimeMs={detail.execution_time_ms} />
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            {/* Full-width StrategyBrief */}
            <StrategyBrief
              brief={detail.strategic_brief as StrategicBrief}
              analysisId={detail.id}
            />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

/* ─── Log Panel ──────────────────────────────────────────────────────────── */

function LogPanel({
  logs,
  logsEndRef,
}: {
  logs: LogEntry[];
  logsEndRef: React.RefObject<HTMLDivElement>;
}) {
  const levelColor = (entry: LogEntry): string => {
    if (entry.level === "error") return "var(--danger)";
    if (entry.level === "success") return "var(--success)";
    if (entry.agent && AGENT_COLORS[entry.agent]) return AGENT_COLORS[entry.agent];
    return "var(--text-secondary)";
  };

  return (
    <div style={{ backgroundColor: "var(--bg-surface)", border: "1px solid var(--border)", borderRadius: "var(--radius-lg)", overflow: "hidden", position: "sticky", top: 20 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "10px 14px", borderBottom: "1px solid var(--border)", backgroundColor: "var(--bg-elevated)" }}>
        <Terminal size={13} style={{ color: "var(--text-tertiary)" }} />
        <span style={{ fontSize: 11, fontWeight: 600, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.05em" }}>
          Pipeline Log
        </span>
        <span style={{ marginLeft: "auto", fontSize: 10, color: "var(--text-tertiary)" }}>
          {logs.length} events
        </span>
      </div>
      <div
        style={{ padding: "12px 14px", height: 420, overflowY: "auto", fontFamily: "var(--font-mono)", fontSize: 11, lineHeight: 1.7 }}
      >
        {logs.length === 0 && (
          <span style={{ color: "var(--text-tertiary)" }}>Awaiting pipeline events…</span>
        )}
        {logs.map((entry, i) => (
          <div key={i} style={{ display: "flex", gap: 8, marginBottom: 1 }}>
            <span style={{ color: "var(--text-tertiary)", flexShrink: 0, fontSize: 10 }}>
              {new Date(entry.ts).toISOString().slice(11, 19)}
            </span>
            <span style={{ color: levelColor(entry), wordBreak: "break-word" }}>
              {entry.message}
            </span>
          </div>
        ))}
        <div ref={logsEndRef} />
      </div>
    </div>
  );
}
