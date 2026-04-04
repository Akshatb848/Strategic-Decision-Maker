"use client";

import { useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { slideUp, fadeIn } from "@/lib/animations";
import { getAnalysis, type AnalysisDetail, type StrategicBrief } from "@/lib/api";
import { AgentTimeline } from "@/components/AgentTimeline";
import { StrategyBrief } from "@/components/StrategyBrief";
import { StatusBadge } from "@/components/ui/Badge";
import { ArrowLeft, Terminal } from "lucide-react";

interface LogEntry {
  ts: number;
  message: string;
  level: "info" | "error" | "success";
}

export default function AnalysisDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [detail, setDetail] = useState<AnalysisDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const logsEndRef = useRef<HTMLDivElement>(null);

  const addLog = (message: string, level: LogEntry["level"] = "info") => {
    setLogs((prev) => [
      ...prev,
      { ts: Date.now(), message, level },
    ]);
  };

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  useEffect(() => {
    if (!id) return;

    addLog(`Loading analysis ${id}…`);

    const load = () =>
      getAnalysis(id)
        .then((d) => {
          setDetail(d);
          addLog(
            `Analysis loaded — status: ${d.status}`,
            d.status === "failed" ? "error" : "info"
          );
          return d;
        })
        .catch((e: Error) => {
          setError(e.message);
          addLog(`Error: ${e.message}`, "error");
          return null;
        });

    load().finally(() => setLoading(false));

    // Poll while running
    const interval = setInterval(async () => {
      const d = await getAnalysis(id).catch(() => null);
      if (!d) return;
      setDetail(d);

      if (d.status === "completed") {
        addLog("Pipeline complete.", "success");
        clearInterval(interval);
      } else if (d.status === "failed") {
        addLog("Pipeline failed.", "error");
        clearInterval(interval);
      } else {
        const running = d.agent_runs.find((r) => r.status === "running");
        if (running) {
          addLog(`[${running.agent_name}] running…`);
        }
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [id]);

  if (loading) {
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          minHeight: "60vh",
          flexDirection: "column",
          gap: 12,
        }}
      >
        <div
          style={{
            width: 32,
            height: 32,
            borderRadius: "50%",
            border: "3px solid var(--border)",
            borderTopColor: "var(--accent)",
            animation: "spin 0.8s linear infinite",
          }}
        />
        <p style={{ fontSize: 13, color: "var(--text-tertiary)" }}>
          Loading analysis…
        </p>
      </div>
    );
  }

  if (error || !detail) {
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          minHeight: "60vh",
          flexDirection: "column",
          gap: 16,
        }}
      >
        <p style={{ fontSize: 14, color: "var(--danger)" }}>
          {error ?? "Analysis not found"}
        </p>
        <Link
          href="/"
          style={{
            fontSize: 13,
            color: "var(--accent)",
            textDecoration: "none",
            display: "flex",
            alignItems: "center",
            gap: 6,
          }}
        >
          <ArrowLeft size={14} />
          Back to dashboard
        </Link>
      </div>
    );
  }

  const isComplete = detail.status === "completed" && detail.strategic_brief != null;

  return (
    <div style={{ padding: "28px 28px 64px" }}>
      {/* Page header */}
      <div style={{ marginBottom: 24 }}>
        <Link
          href="/"
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 6,
            fontSize: 12,
            color: "var(--text-tertiary)",
            textDecoration: "none",
            marginBottom: 12,
            transition: "color var(--transition-fast)",
          }}
          onMouseEnter={(e) => {
            (e.currentTarget as HTMLAnchorElement).style.color =
              "var(--text-secondary)";
          }}
          onMouseLeave={(e) => {
            (e.currentTarget as HTMLAnchorElement).style.color =
              "var(--text-tertiary)";
          }}
        >
          <ArrowLeft size={12} />
          Dashboard
        </Link>

        <div
          style={{
            display: "flex",
            alignItems: "flex-start",
            justifyContent: "space-between",
            gap: 16,
          }}
        >
          <div>
            <h1
              style={{
                fontSize: 18,
                fontWeight: 700,
                color: "var(--text-primary)",
                letterSpacing: "-0.02em",
                lineHeight: 1.3,
                marginBottom: 6,
              }}
            >
              {detail.query}
            </h1>
            <p style={{ fontSize: 12, color: "var(--text-tertiary)" }}>
              {detail.company_context.company_name} ·{" "}
              {detail.company_context.sector} ·{" "}
              {detail.company_context.target_market}
            </p>
          </div>
          <StatusBadge status={detail.status} />
        </div>
      </div>

      {/* Main layout: 60% left + 40% right */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "60fr 40fr",
          gap: 20,
          alignItems: "flex-start",
        }}
      >
        {/* Left: AgentTimeline */}
        <div>
          <AgentTimeline
            agentRuns={detail.agent_runs}
            status={detail.status}
            executionTimeMs={detail.execution_time_ms}
          />

          {/* Running indicator */}
          {detail.status === "running" && (
            <div
              style={{
                marginTop: 12,
                padding: "10px 14px",
                backgroundColor: "var(--accent-dim)",
                borderRadius: "var(--radius-md)",
                border: "1px solid rgba(124,58,237,0.25)",
                display: "flex",
                alignItems: "center",
                gap: 8,
                fontSize: 12,
                color: "var(--accent)",
              }}
            >
              <div
                style={{
                  width: 10,
                  height: 10,
                  borderRadius: "50%",
                  border: "2px solid transparent",
                  borderTopColor: "var(--accent)",
                  animation: "spin 0.7s linear infinite",
                  flexShrink: 0,
                }}
              />
              ASIS agents are working… typically 2–4 minutes
            </div>
          )}
        </div>

        {/* Right: Log panel or StrategyBrief */}
        <div>
          <AnimatePresence mode="wait">
            {!isComplete ? (
              <motion.div
                key="logs"
                initial={fadeIn.initial}
                animate={fadeIn.animate}
                exit={{ opacity: 0 }}
                transition={fadeIn.transition}
              >
                <LogPanel logs={logs} logsEndRef={logsEndRef} />
              </motion.div>
            ) : (
              <motion.div
                key="brief"
                initial={slideUp.initial}
                animate={slideUp.animate}
                transition={slideUp.transition}
              >
                <StrategyBrief
                  brief={detail.strategic_brief as StrategicBrief}
                  analysisId={detail.id}
                />
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
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
  const levelColor: Record<LogEntry["level"], string> = {
    info: "var(--text-secondary)",
    error: "var(--danger)",
    success: "var(--success)",
  };

  return (
    <div
      style={{
        backgroundColor: "var(--bg-surface)",
        border: "1px solid var(--border)",
        borderRadius: "var(--radius-lg)",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          padding: "10px 14px",
          borderBottom: "1px solid var(--border)",
          backgroundColor: "var(--bg-elevated)",
        }}
      >
        <Terminal size={13} style={{ color: "var(--text-tertiary)" }} />
        <span
          style={{
            fontSize: 11,
            fontWeight: 600,
            color: "var(--text-secondary)",
            textTransform: "uppercase",
            letterSpacing: "0.05em",
          }}
        >
          Pipeline Log
        </span>
      </div>
      <div
        style={{
          padding: "12px 14px",
          height: 320,
          overflowY: "auto",
          fontFamily: "var(--font-mono)",
          fontSize: 11,
          lineHeight: 1.7,
        }}
      >
        {logs.length === 0 && (
          <span style={{ color: "var(--text-tertiary)" }}>
            Awaiting pipeline events…
          </span>
        )}
        {logs.map((entry, i) => (
          <div key={i} style={{ display: "flex", gap: 8 }}>
            <span style={{ color: "var(--text-tertiary)", flexShrink: 0 }}>
              {new Date(entry.ts).toISOString().slice(11, 19)}
            </span>
            <span style={{ color: levelColor[entry.level] }}>
              {entry.message}
            </span>
          </div>
        ))}
        <div ref={logsEndRef} />
      </div>
    </div>
  );
}
