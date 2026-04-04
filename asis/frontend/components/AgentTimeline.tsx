"use client";

import { motion } from "framer-motion";
import { staggerContainer, staggerItem } from "@/lib/animations";
import { StatusDot } from "@/components/ui/StatusDot";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { Card, CardHeader, CardTitle } from "@/components/ui/Card";
import type { AgentRunSummary } from "@/lib/api";

const AGENT_LABELS: Record<string, string> = {
  orchestrator: "Orchestrator",
  market_intelligence: "Market Intelligence",
  risk_assessment: "Risk Assessment",
  financial_reasoning: "Financial Reasoning",
  competitor_analysis: "Competitor Analysis",
  synthesis: "Synthesis",
};

const AGENT_ORDER = [
  "orchestrator",
  "market_intelligence",
  "risk_assessment",
  "competitor_analysis",
  "financial_reasoning",
  "synthesis",
];

interface Props {
  agentRuns: AgentRunSummary[];
  status: string;
  executionTimeMs: number | null;
}

function statusToDot(
  s: AgentRunSummary["status"]
): "idle" | "running" | "done" | "error" | "queued" {
  switch (s) {
    case "completed": return "done";
    case "running":   return "running";
    case "error":     return "error";
    case "skipped":   return "idle";
    default:          return "queued";
  }
}

function progressFromStatus(run: AgentRunSummary | undefined): number {
  if (!run) return 0;
  if (run.status === "completed") return 100;
  if (run.status === "running") return 55;
  if (run.status === "error") return 100;
  return 0;
}

export function AgentTimeline({ agentRuns, status, executionTimeMs }: Props) {
  const byName = Object.fromEntries(agentRuns.map((r) => [r.agent_name, r]));

  return (
    <Card padding="none">
      <CardHeader
        className=""
        style={{
          padding: "14px 16px",
          borderBottom: "1px solid var(--border)",
          marginBottom: 0,
        }}
      >
        <CardTitle>Agent Pipeline</CardTitle>
        {executionTimeMs != null && (
          <span
            style={{
              fontSize: 11,
              color: "var(--text-tertiary)",
              fontVariantNumeric: "tabular-nums",
              fontFamily: "var(--font-mono)",
            }}
          >
            {(executionTimeMs / 1000).toFixed(1)}s total
          </span>
        )}
      </CardHeader>

      <motion.div
        variants={staggerContainer}
        initial="initial"
        animate="animate"
        style={{ padding: "8px 0" }}
      >
        {AGENT_ORDER.map((name, i) => {
          const run = byName[name];
          const agentStatus = run?.status ?? "idle";
          const dotStatus = statusToDot(agentStatus);
          const progress = progressFromStatus(run);
          const isRunning = agentStatus === "running";
          const isDone = agentStatus === "completed";
          const isError = agentStatus === "error";

          return (
            <motion.div key={name} variants={staggerItem}>
              <div
                style={{
                  display: "flex",
                  gap: 12,
                  padding: "10px 16px",
                  backgroundColor: isRunning
                    ? "rgba(124,58,237,0.06)"
                    : isDone
                    ? "rgba(34,197,94,0.04)"
                    : isError
                    ? "rgba(239,68,68,0.04)"
                    : "transparent",
                  borderLeft: isRunning
                    ? "2px solid var(--accent)"
                    : isDone
                    ? "2px solid var(--success)"
                    : isError
                    ? "2px solid var(--danger)"
                    : "2px solid transparent",
                  transition: "all var(--transition-base)",
                }}
              >
                {/* Timeline left: dot + connector */}
                <div
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    gap: 0,
                    paddingTop: 2,
                  }}
                >
                  <StatusDot status={dotStatus} size={9} />
                  {i < AGENT_ORDER.length - 1 && (
                    <div
                      style={{
                        width: 1,
                        flex: 1,
                        minHeight: 16,
                        backgroundColor: isDone
                          ? "var(--success)"
                          : "var(--border)",
                        marginTop: 4,
                        opacity: 0.5,
                      }}
                    />
                  )}
                </div>

                {/* Agent info */}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "baseline",
                      marginBottom: 4,
                    }}
                  >
                    <span
                      style={{
                        fontSize: 12,
                        fontWeight: 500,
                        color: isRunning
                          ? "var(--accent)"
                          : isDone
                          ? "var(--success)"
                          : isError
                          ? "var(--danger)"
                          : "var(--text-tertiary)",
                      }}
                    >
                      {AGENT_LABELS[name] ?? name}
                    </span>

                    <div
                      style={{
                        display: "flex",
                        gap: 8,
                        alignItems: "center",
                      }}
                    >
                      {run?.tokens_used != null && (
                        <span
                          style={{
                            fontSize: 10,
                            color: "var(--text-tertiary)",
                            fontFamily: "var(--font-mono)",
                          }}
                        >
                          {run.tokens_used.toLocaleString()}t
                        </span>
                      )}
                      {run?.duration_ms != null && (
                        <span
                          style={{
                            fontSize: 10,
                            color: "var(--text-tertiary)",
                            fontFamily: "var(--font-mono)",
                          }}
                        >
                          {(run.duration_ms / 1000).toFixed(1)}s
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Progress bar */}
                  {agentStatus !== "idle" && agentStatus !== "skipped" && (
                    <ProgressBar
                      width={progress}
                      height={3}
                      color={
                        isError
                          ? "var(--danger)"
                          : isDone
                          ? "var(--success)"
                          : "var(--accent)"
                      }
                      animated
                    />
                  )}

                  {/* Extended info row */}
                  {(run?.error_message != null) && (
                    <p
                      style={{
                        fontSize: 10,
                        color: "var(--danger)",
                        marginTop: 4,
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {run.error_message}
                    </p>
                  )}
                </div>
              </div>
            </motion.div>
          );
        })}
      </motion.div>

      {/* Pipeline status footer */}
      {(status === "completed" || status === "failed") && (
        <div
          style={{
            padding: "10px 16px",
            borderTop: "1px solid var(--border)",
            display: "flex",
            justifyContent: "center",
          }}
        >
          <span
            style={{
              fontSize: 11,
              fontWeight: 600,
              color:
                status === "completed" ? "var(--success)" : "var(--danger)",
              textTransform: "uppercase",
              letterSpacing: "0.06em",
            }}
          >
            Pipeline {status === "completed" ? "Complete" : "Failed"}
          </span>
        </div>
      )}
    </Card>
  );
}
