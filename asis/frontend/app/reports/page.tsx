"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { listReports, type AnalysisSummary } from "@/lib/api";
import { formatDistanceToNow } from "date-fns";
import { ArrowLeft, Cpu, ChevronRight, Clock } from "lucide-react";

export default function ReportsPage() {
  const [analyses, setAnalyses] = useState<AnalysisSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const PAGE_SIZE = 20;

  useEffect(() => {
    setLoading(true);
    listReports(page, PAGE_SIZE)
      .then((res) => {
        setAnalyses(res.items);
        setTotal(res.total);
      })
      .finally(() => setLoading(false));
  }, [page]);

  return (
    <div className="min-h-screen bg-surface">
      <header className="border-b border-surface-border px-8 py-4 flex items-center gap-4">
        <Link href="/" className="text-gray-400 hover:text-white transition-colors">
          <ArrowLeft size={20} />
        </Link>
        <div className="flex items-center gap-3">
          <div className="w-7 h-7 bg-brand-500 rounded-md flex items-center justify-center">
            <Cpu size={15} className="text-white" />
          </div>
          <span className="text-white font-semibold text-sm">All Reports</span>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-8 py-10">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h2 className="text-2xl font-bold text-white">Strategic Reports</h2>
            <p className="text-gray-500 text-sm mt-1">{total} analyses total</p>
          </div>
          <Link href="/analysis/new" className="btn-primary text-sm">
            + New Analysis
          </Link>
        </div>

        {loading && (
          <div className="flex justify-center py-16">
            <span className="w-8 h-8 border-4 border-brand-500/30 border-t-brand-500 rounded-full animate-spin" />
          </div>
        )}

        {!loading && (
          <div className="card divide-y divide-surface-border">
            {analyses.length === 0 && (
              <div className="py-12 text-center text-gray-500">No reports yet.</div>
            )}
            {analyses.map((a) => (
              <Link
                key={a.id}
                href={`/analysis/${a.id}`}
                className="flex items-center justify-between py-4 hover:bg-white/5 -mx-6 px-6 transition-colors"
              >
                <div className="flex-1 min-w-0 mr-4">
                  <p className="text-white text-sm font-medium truncate">{a.query}</p>
                  <div className="flex items-center gap-4 mt-1">
                    <span className="text-gray-500 text-xs flex items-center gap-1">
                      <Clock size={11} />
                      {formatDistanceToNow(new Date(a.created_at), { addSuffix: true })}
                    </span>
                    {a.execution_time_ms && (
                      <span className="text-gray-600 text-xs">
                        {(a.execution_time_ms / 1000).toFixed(0)}s
                      </span>
                    )}
                    {a.confidence_score != null && (
                      <span className="text-gray-500 text-xs">
                        Confidence: {a.confidence_score.toFixed(1)}/10
                      </span>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-3 shrink-0">
                  <StatusBadge status={a.status} />
                  <ChevronRight size={16} className="text-gray-600" />
                </div>
              </Link>
            ))}
          </div>
        )}

        {/* Pagination */}
        {total > PAGE_SIZE && (
          <div className="flex justify-center gap-2 mt-6">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="btn-secondary text-sm disabled:opacity-40"
            >
              Previous
            </button>
            <span className="flex items-center text-gray-500 text-sm px-2">
              Page {page} of {Math.ceil(total / PAGE_SIZE)}
            </span>
            <button
              onClick={() => setPage((p) => p + 1)}
              disabled={page >= Math.ceil(total / PAGE_SIZE)}
              className="btn-secondary text-sm disabled:opacity-40"
            >
              Next
            </button>
          </div>
        )}
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
