"use client";

import type { AgentRunSummary } from "@/lib/api";
import { CheckCircle, XCircle, Circle, Loader2, MinusCircle } from "lucide-react";

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

export function AgentStatusPanel({ agentRuns, status, executionTimeMs }: Props) {
  const byName = Object.fromEntries(agentRuns.map((r) => [r.agent_name, r]));

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-white font-medium text-sm">Agent Pipeline</h3>
        {executionTimeMs && (
          <span className="text-gray-500 text-xs">
            {(executionTimeMs / 1000).toFixed(1)}s
          </span>
        )}
      </div>

      <div className="space-y-2">
        {AGENT_ORDER.map((name, i) => {
          const run = byName[name];
          const agentStatus = run?.status ?? "idle";

          return (
            <div key={name}>
              <div
                className={`flex items-center gap-3 p-3 rounded-lg border transition-all ${
                  agentStatus === "running"
                    ? "border-brand-500/50 bg-brand-900/20"
                    : agentStatus === "completed"
                    ? "border-emerald-800/30 bg-emerald-900/10"
                    : agentStatus === "error"
                    ? "border-red-800/30 bg-red-900/10"
                    : "border-surface-border bg-transparent"
                }`}
              >
                <StatusIcon status={agentStatus} />
                <div className="flex-1 min-w-0">
                  <p
                    className={`text-xs font-medium ${
                      agentStatus === "running"
                        ? "text-brand-300"
                        : agentStatus === "completed"
                        ? "text-emerald-300"
                        : agentStatus === "error"
                        ? "text-red-300"
                        : "text-gray-500"
                    }`}
                  >
                    {AGENT_LABELS[name] ?? name}
                  </p>
                  {run?.duration_ms && (
                    <p className="text-gray-600 text-xs">
                      {(run.duration_ms / 1000).toFixed(1)}s
                      {run.tokens_used ? ` · ${run.tokens_used.toLocaleString()} tokens` : ""}
                    </p>
                  )}
                  {run?.error_message && (
                    <p className="text-red-400 text-xs truncate">{run.error_message}</p>
                  )}
                </div>
              </div>
              {/* Connector line */}
              {i < AGENT_ORDER.length - 1 && (
                <div className="ml-[22px] w-px h-2 bg-surface-border" />
              )}
            </div>
          );
        })}
      </div>

      {/* Overall status */}
      {status === "completed" && (
        <div className="mt-4 pt-4 border-t border-surface-border text-center">
          <span className="badge badge-green">Pipeline Complete</span>
        </div>
      )}
      {status === "failed" && (
        <div className="mt-4 pt-4 border-t border-surface-border text-center">
          <span className="badge badge-red">Pipeline Failed</span>
        </div>
      )}
    </div>
  );
}

function StatusIcon({ status }: { status: string }) {
  const cls = "shrink-0";
  switch (status) {
    case "completed":
      return <CheckCircle size={16} className={`${cls} text-emerald-400`} />;
    case "running":
      return <Loader2 size={16} className={`${cls} text-brand-400 animate-spin`} />;
    case "error":
      return <XCircle size={16} className={`${cls} text-red-400`} />;
    case "skipped":
      return <MinusCircle size={16} className={`${cls} text-gray-600`} />;
    default:
      return <Circle size={16} className={`${cls} text-gray-700`} />;
  }
}
