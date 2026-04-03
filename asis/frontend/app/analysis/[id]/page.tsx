"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { getAnalysis, type AnalysisDetail, type StrategicBrief } from "@/lib/api";
import { AgentStatusPanel } from "@/components/AgentStatusPanel";
import { StrategyBrief } from "@/components/StrategyBrief";
import { ArrowLeft, Cpu } from "lucide-react";

export default function AnalysisDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [detail, setDetail] = useState<AnalysisDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;

    const load = () =>
      getAnalysis(id)
        .then(setDetail)
        .catch((e) => setError(e.message));

    load().finally(() => setLoading(false));

    // Poll while running
    let interval: ReturnType<typeof setInterval> | null = null;
    const startPolling = () => {
      interval = setInterval(() => {
        getAnalysis(id).then((d) => {
          setDetail(d);
          if (d.status === "completed" || d.status === "failed") {
            clearInterval(interval!);
          }
        });
      }, 3000);
    };

    startPolling();
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [id]);

  if (loading) {
    return (
      <div className="min-h-screen bg-surface flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <span className="w-10 h-10 border-4 border-brand-500/30 border-t-brand-500 rounded-full animate-spin" />
          <p className="text-gray-400 text-sm">Loading analysis…</p>
        </div>
      </div>
    );
  }

  if (error || !detail) {
    return (
      <div className="min-h-screen bg-surface flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-400 mb-4">{error ?? "Analysis not found"}</p>
          <Link href="/" className="btn-secondary">Back to dashboard</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-surface">
      {/* Header */}
      <header className="border-b border-surface-border px-8 py-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/" className="text-gray-400 hover:text-white transition-colors">
            <ArrowLeft size={20} />
          </Link>
          <div className="flex items-center gap-3">
            <div className="w-7 h-7 bg-brand-500 rounded-md flex items-center justify-center">
              <Cpu size={15} className="text-white" />
            </div>
            <span className="text-white font-semibold text-sm">Analysis Report</span>
          </div>
        </div>
        <StatusBadge status={detail.status} />
      </header>

      <main className="max-w-6xl mx-auto px-8 py-8">
        {/* Query */}
        <div className="mb-6">
          <h2 className="text-xl font-bold text-white mb-1 leading-snug">{detail.query}</h2>
          <p className="text-gray-500 text-sm">
            {detail.company_context.company_name} · {detail.company_context.sector} ·{" "}
            {detail.company_context.target_market}
          </p>
        </div>

        <div className="grid grid-cols-3 gap-6">
          {/* Left: Agent Status Panel */}
          <div className="col-span-1">
            <AgentStatusPanel
              agentRuns={detail.agent_runs}
              status={detail.status}
              executionTimeMs={detail.execution_time_ms}
            />
          </div>

          {/* Right: Strategic Brief */}
          <div className="col-span-2">
            {detail.status === "running" && !detail.strategic_brief && (
              <div className="card flex flex-col items-center py-16">
                <span className="w-10 h-10 border-4 border-brand-500/30 border-t-brand-500 rounded-full animate-spin mb-4" />
                <p className="text-gray-400 text-sm">ASIS agents are working…</p>
                <p className="text-gray-600 text-xs mt-1">This typically takes 2-4 minutes</p>
              </div>
            )}
            {detail.status === "failed" && (
              <div className="card border-red-800/50 bg-red-900/10">
                <p className="text-red-400 font-medium mb-2">Pipeline failed</p>
                <p className="text-gray-400 text-sm">{detail.query}</p>
              </div>
            )}
            {detail.strategic_brief && (
              <StrategyBrief
                brief={detail.strategic_brief as StrategicBrief}
                analysisId={detail.id}
              />
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const cls =
    status === "completed" ? "badge-green"
    : status === "running" ? "badge-blue"
    : status === "failed" ? "badge-red"
    : "badge-gray";
  return <span className={`badge ${cls} capitalize`}>{status}</span>;
}
