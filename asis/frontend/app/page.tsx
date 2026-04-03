"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { listReports, type AnalysisSummary } from "@/lib/api";
import { formatDistanceToNow } from "date-fns";
import { BarChart3, Plus, FileText, Cpu, TrendingUp, Shield } from "lucide-react";

export default function DashboardPage() {
  const [analyses, setAnalyses] = useState<AnalysisSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listReports(1, 10)
      .then((res) => setAnalyses(res.items))
      .catch(() => setError("Could not load analyses"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="min-h-screen bg-surface">
      {/* Header */}
      <header className="border-b border-surface-border px-8 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-brand-500 rounded-lg flex items-center justify-center">
            <Cpu size={18} className="text-white" />
          </div>
          <div>
            <h1 className="text-white font-semibold text-sm">ASIS</h1>
            <p className="text-gray-500 text-xs">Autonomous Strategic Intelligence System</p>
          </div>
        </div>
        <Link href="/analysis/new" className="btn-primary flex items-center gap-2">
          <Plus size={16} />
          New Analysis
        </Link>
      </header>

      <main className="max-w-6xl mx-auto px-8 py-10">
        {/* Hero */}
        <div className="mb-10">
          <h2 className="text-3xl font-bold text-white mb-2">Strategic Intelligence Dashboard</h2>
          <p className="text-gray-400">
            Board-level strategic analysis powered by six specialised AI agents.
          </p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-4 mb-10">
          {[
            { icon: BarChart3, label: "Total Analyses", value: analyses.length },
            {
              icon: TrendingUp,
              label: "Completed",
              value: analyses.filter((a) => a.status === "completed").length,
            },
            {
              icon: Shield,
              label: "Avg Confidence",
              value: avgScore(analyses, "confidence_score"),
            },
          ].map(({ icon: Icon, label, value }) => (
            <div key={label} className="card flex items-center gap-4">
              <div className="w-10 h-10 bg-brand-900/30 rounded-lg flex items-center justify-center">
                <Icon size={20} className="text-brand-400" />
              </div>
              <div>
                <p className="text-gray-400 text-xs">{label}</p>
                <p className="text-white font-semibold text-xl">{value}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Recent analyses */}
        <div className="card">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-white font-semibold">Recent Analyses</h3>
            <Link href="/reports" className="text-brand-400 text-sm hover:text-brand-300">
              View all
            </Link>
          </div>

          {loading && (
            <div className="text-center py-12 text-gray-500">Loading analyses…</div>
          )}
          {error && (
            <div className="text-center py-12 text-red-400">{error}</div>
          )}
          {!loading && !error && analyses.length === 0 && (
            <div className="text-center py-12">
              <FileText size={36} className="text-gray-600 mx-auto mb-3" />
              <p className="text-gray-400 mb-4">No analyses yet.</p>
              <Link href="/analysis/new" className="btn-primary inline-flex items-center gap-2">
                <Plus size={16} /> Start your first analysis
              </Link>
            </div>
          )}
          {!loading && analyses.length > 0 && (
            <div className="divide-y divide-surface-border">
              {analyses.map((a) => (
                <Link
                  key={a.id}
                  href={`/analysis/${a.id}`}
                  className="flex items-center justify-between py-4 hover:bg-white/5 -mx-6 px-6 rounded-lg transition-colors"
                >
                  <div className="flex-1 min-w-0 mr-4">
                    <p className="text-white text-sm font-medium truncate">{a.query}</p>
                    <p className="text-gray-500 text-xs mt-0.5">
                      {formatDistanceToNow(new Date(a.created_at), { addSuffix: true })}
                    </p>
                  </div>
                  <div className="flex items-center gap-3 shrink-0">
                    {a.confidence_score != null && (
                      <span className="text-xs text-gray-400">
                        {a.confidence_score.toFixed(1)}/10
                      </span>
                    )}
                    <StatusBadge status={a.status} />
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const cls =
    status === "completed"
      ? "badge-green"
      : status === "running"
      ? "badge-blue"
      : status === "failed"
      ? "badge-red"
      : "badge-gray";
  return <span className={`badge ${cls}`}>{status}</span>;
}

function avgScore(
  analyses: AnalysisSummary[],
  key: "confidence_score" | "data_quality_score"
): string {
  const scores = analyses.map((a) => a[key]).filter((s): s is number => s != null);
  if (!scores.length) return "—";
  return (scores.reduce((a, b) => a + b, 0) / scores.length).toFixed(1);
}
