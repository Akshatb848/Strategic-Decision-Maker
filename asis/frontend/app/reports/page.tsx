"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { staggerContainer, staggerItem, fadeUp } from "@/lib/animations";
import { listReports, type AnalysisSummary } from "@/lib/api";
import { formatDistanceToNow } from "date-fns";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { StatusBadge } from "@/components/ui/Badge";
import { StatusDot } from "@/components/ui/StatusDot";
import {
  Search,
  ChevronRight,
  ChevronLeft,
  Download,
  Plus,
  Clock,
  AlertCircle,
} from "lucide-react";

type StatusFilter = "all" | "completed" | "running" | "failed" | "pending";

const PAGE_SIZE = 20;

export default function ReportsPage() {
  const [analyses, setAnalyses] = useState<AnalysisSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    listReports(page, PAGE_SIZE)
      .then((res) => {
        setAnalyses(res.items);
        setTotal(res.total);
      })
      .catch(() => setError("Could not load reports"))
      .finally(() => setLoading(false));
  }, [page]);

  useEffect(() => {
    load();
  }, [load]);

  const filtered = analyses.filter((a) => {
    const matchSearch =
      search === "" ||
      a.query.toLowerCase().includes(search.toLowerCase());
    const matchStatus =
      statusFilter === "all" || a.status === statusFilter;
    return matchSearch && matchStatus;
  });

  const totalPages = Math.ceil(total / PAGE_SIZE);

  const handleExport = () => {
    const csv = [
      ["ID", "Query", "Status", "Created", "Duration (s)", "Confidence"].join(","),
      ...filtered.map((a) =>
        [
          a.id,
          `"${a.query.replace(/"/g, '""')}"`,
          a.status,
          a.created_at,
          a.execution_time_ms != null
            ? (a.execution_time_ms / 1000).toFixed(0)
            : "",
          a.confidence_score != null ? a.confidence_score.toFixed(1) : "",
        ].join(",")
      ),
    ].join("\n");

    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `asis-reports-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div style={{ padding: "32px 32px 64px" }}>
      {/* Header */}
      <motion.div
        initial={fadeUp.initial}
        animate={fadeUp.animate}
        transition={fadeUp.transition}
        style={{
          display: "flex",
          alignItems: "flex-end",
          justifyContent: "space-between",
          marginBottom: 24,
        }}
      >
        <div>
          <h1
            style={{
              fontSize: 22,
              fontWeight: 700,
              color: "var(--text-primary)",
              letterSpacing: "-0.02em",
              marginBottom: 4,
            }}
          >
            Strategic Reports
          </h1>
          <p style={{ fontSize: 13, color: "var(--text-secondary)" }}>
            {loading ? "Loading…" : `${total} analyses total`}
          </p>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <Button
            variant="outline"
            size="sm"
            leftIcon={<Download size={13} />}
            onClick={handleExport}
            disabled={filtered.length === 0}
          >
            Export CSV
          </Button>
          <Link href="/analysis/new">
            <Button variant="primary" size="sm" leftIcon={<Plus size={13} />}>
              New Analysis
            </Button>
          </Link>
        </div>
      </motion.div>

      {/* Filters */}
      <motion.div
        initial={fadeUp.initial}
        animate={fadeUp.animate}
        transition={{ ...fadeUp.transition, delay: 0.05 }}
        style={{
          display: "flex",
          gap: 10,
          marginBottom: 16,
          flexWrap: "wrap",
          alignItems: "center",
        }}
      >
        {/* Search */}
        <div style={{ position: "relative", flex: "1 1 240px", maxWidth: 360 }}>
          <Search
            size={13}
            style={{
              position: "absolute",
              left: 10,
              top: "50%",
              transform: "translateY(-50%)",
              color: "var(--text-tertiary)",
              pointerEvents: "none",
            }}
          />
          <input
            type="text"
            placeholder="Search analyses…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{
              width: "100%",
              paddingLeft: 30,
              paddingRight: 12,
              paddingTop: 7,
              paddingBottom: 7,
              borderRadius: "var(--radius-md)",
              border: "1px solid var(--border)",
              backgroundColor: "var(--bg-surface)",
              color: "var(--text-primary)",
              fontSize: 13,
              outline: "none",
            }}
          />
        </div>

        {/* Status filters */}
        <div style={{ display: "flex", gap: 4 }}>
          {(["all", "completed", "running", "failed", "pending"] as StatusFilter[]).map(
            (s) => (
              <button
                key={s}
                type="button"
                onClick={() => setStatusFilter(s)}
                style={{
                  padding: "5px 10px",
                  borderRadius: "var(--radius-sm)",
                  border:
                    statusFilter === s
                      ? "1px solid var(--accent)"
                      : "1px solid var(--border)",
                  backgroundColor:
                    statusFilter === s
                      ? "var(--accent-dim)"
                      : "var(--bg-surface)",
                  color:
                    statusFilter === s ? "var(--accent)" : "var(--text-secondary)",
                  fontSize: 12,
                  fontWeight: statusFilter === s ? 600 : 400,
                  cursor: "pointer",
                  transition: "all var(--transition-fast)",
                  textTransform: "capitalize",
                }}
              >
                {s}
              </button>
            )
          )}
        </div>
      </motion.div>

      {/* Table */}
      <motion.div
        initial={fadeUp.initial}
        animate={fadeUp.animate}
        transition={{ ...fadeUp.transition, delay: 0.1 }}
      >
        <Card padding="none">
          {/* Table header row */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 80px 80px 100px 32px",
              gap: 0,
              padding: "8px 20px",
              borderBottom: "1px solid var(--border)",
              backgroundColor: "var(--bg-elevated)",
            }}
          >
            {["Query", "Status", "Duration", "Confidence", ""].map((col) => (
              <span
                key={col}
                style={{
                  fontSize: 10,
                  fontWeight: 600,
                  color: "var(--text-tertiary)",
                  textTransform: "uppercase",
                  letterSpacing: "0.05em",
                }}
              >
                {col}
              </span>
            ))}
          </div>

          {/* Loading */}
          {loading && (
            <div
              style={{
                padding: "48px 20px",
                textAlign: "center",
                color: "var(--text-tertiary)",
                fontSize: 13,
              }}
            >
              <div
                style={{
                  width: 20,
                  height: 20,
                  borderRadius: "50%",
                  border: "2px solid var(--border)",
                  borderTopColor: "var(--accent)",
                  animation: "spin 0.8s linear infinite",
                  margin: "0 auto 10px",
                }}
              />
              Loading reports…
            </div>
          )}

          {/* Error */}
          {error && (
            <div
              style={{
                padding: "48px 20px",
                textAlign: "center",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                gap: 8,
              }}
            >
              <AlertCircle size={20} style={{ color: "var(--danger)", opacity: 0.7 }} />
              <p style={{ fontSize: 13, color: "var(--danger)" }}>{error}</p>
              <button
                type="button"
                onClick={load}
                style={{
                  fontSize: 12,
                  color: "var(--accent)",
                  background: "none",
                  border: "none",
                  cursor: "pointer",
                  textDecoration: "underline",
                }}
              >
                Retry
              </button>
            </div>
          )}

          {/* Empty */}
          {!loading && !error && filtered.length === 0 && (
            <div
              style={{
                padding: "48px 20px",
                textAlign: "center",
                color: "var(--text-tertiary)",
                fontSize: 13,
              }}
            >
              {search || statusFilter !== "all"
                ? "No reports match your filters."
                : "No reports yet."}
            </div>
          )}

          {/* Rows */}
          {!loading && !error && filtered.length > 0 && (
            <motion.div
              variants={staggerContainer}
              initial="initial"
              animate="animate"
            >
              {filtered.map((a, i) => (
                <motion.div key={a.id} variants={staggerItem}>
                  <Link
                    href={`/analysis/${a.id}`}
                    style={{
                      display: "grid",
                      gridTemplateColumns: "1fr 80px 80px 100px 32px",
                      gap: 0,
                      padding: "12px 20px",
                      alignItems: "center",
                      borderBottom:
                        i < filtered.length - 1
                          ? "1px solid var(--border)"
                          : "none",
                      textDecoration: "none",
                      transition: "background-color var(--transition-fast)",
                    }}
                    onMouseEnter={(e) => {
                      (e.currentTarget as HTMLAnchorElement).style.backgroundColor =
                        "var(--bg-elevated)";
                    }}
                    onMouseLeave={(e) => {
                      (e.currentTarget as HTMLAnchorElement).style.backgroundColor =
                        "transparent";
                    }}
                  >
                    {/* Query + meta */}
                    <div style={{ minWidth: 0 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <StatusDot
                          status={
                            a.status === "completed"
                              ? "done"
                              : a.status === "running"
                              ? "running"
                              : a.status === "failed"
                              ? "error"
                              : "queued"
                          }
                          size={7}
                        />
                        <p
                          style={{
                            fontSize: 13,
                            fontWeight: 500,
                            color: "var(--text-primary)",
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            whiteSpace: "nowrap",
                          }}
                        >
                          {a.query}
                        </p>
                      </div>
                      <p
                        style={{
                          fontSize: 11,
                          color: "var(--text-tertiary)",
                          marginTop: 3,
                          marginLeft: 15,
                          display: "flex",
                          alignItems: "center",
                          gap: 4,
                        }}
                      >
                        <Clock size={10} />
                        {formatDistanceToNow(new Date(a.created_at), {
                          addSuffix: true,
                        })}
                      </p>
                    </div>

                    {/* Status badge */}
                    <div>
                      <StatusBadge status={a.status} />
                    </div>

                    {/* Duration */}
                    <span
                      style={{
                        fontSize: 12,
                        color: "var(--text-tertiary)",
                        fontFamily: "var(--font-mono)",
                      }}
                    >
                      {a.execution_time_ms != null
                        ? `${(a.execution_time_ms / 1000).toFixed(0)}s`
                        : "—"}
                    </span>

                    {/* Confidence */}
                    <span
                      style={{
                        fontSize: 12,
                        color:
                          a.confidence_score != null && a.confidence_score >= 7.5
                            ? "var(--success)"
                            : a.confidence_score != null && a.confidence_score >= 5
                            ? "var(--warning)"
                            : a.confidence_score != null
                            ? "var(--danger)"
                            : "var(--text-tertiary)",
                        fontFamily: "var(--font-mono)",
                        fontWeight: 600,
                      }}
                    >
                      {a.confidence_score != null
                        ? `${a.confidence_score.toFixed(1)}/10`
                        : "—"}
                    </span>

                    {/* Arrow */}
                    <ChevronRight
                      size={14}
                      style={{ color: "var(--text-tertiary)" }}
                    />
                  </Link>
                </motion.div>
              ))}
            </motion.div>
          )}
        </Card>
      </motion.div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div
          style={{
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
            gap: 10,
            marginTop: 20,
          }}
        >
          <Button
            variant="outline"
            size="sm"
            leftIcon={<ChevronLeft size={13} />}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
          >
            Previous
          </Button>
          <span
            style={{
              fontSize: 12,
              color: "var(--text-secondary)",
              padding: "0 8px",
            }}
          >
            Page {page} of {totalPages}
          </span>
          <Button
            variant="outline"
            size="sm"
            rightIcon={<ChevronRight size={13} />}
            onClick={() => setPage((p) => p + 1)}
            disabled={page >= totalPages}
          >
            Next
          </Button>
        </div>
      )}
    </div>
  );
}
