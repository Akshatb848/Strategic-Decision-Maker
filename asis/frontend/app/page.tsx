"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { listReports, type AnalysisSummary } from "@/lib/api";
import { formatDistanceToNow } from "date-fns";
import { staggerContainer, staggerItem, fadeUp } from "@/lib/animations";
import { Card } from "@/components/ui/Card";
import { StatusBadge } from "@/components/ui/Badge";
import { StatusDot } from "@/components/ui/StatusDot";
import {
  BarChart3,
  Plus,
  FileText,
  TrendingUp,
  Shield,
  Clock,
  AlertCircle,
  ChevronRight,
} from "lucide-react";

export default function DashboardPage() {
  const [analyses, setAnalyses] = useState<AnalysisSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listReports(1, 10)
      .then((res) => {
        setAnalyses(res.items);
        setTotal(res.total);
      })
      .catch(() => setError("Could not load analyses"))
      .finally(() => setLoading(false));
  }, []);

  const completed = analyses.filter((a) => a.status === "completed").length;
  const avgConf = avgScore(analyses, "confidence_score");
  const avgDur = avgDuration(analyses);

  const stats = [
    {
      icon: BarChart3,
      label: "Total Analyses",
      value: loading ? "—" : String(total),
      sub: "all time",
    },
    {
      icon: TrendingUp,
      label: "Completed",
      value: loading ? "—" : String(completed),
      sub: "successfully",
    },
    {
      icon: Shield,
      label: "Avg Confidence",
      value: loading ? "—" : avgConf,
      sub: "out of 10",
    },
    {
      icon: Clock,
      label: "Avg Duration",
      value: loading ? "—" : avgDur,
      sub: "per analysis",
    },
  ];

  return (
    <div style={{ padding: "32px 32px 64px" }}>
      {/* Page header */}
      <motion.div
        initial={fadeUp.initial}
        animate={fadeUp.animate}
        transition={fadeUp.transition}
        style={{ marginBottom: 28 }}
      >
        <h1
          style={{
            fontSize: 22,
            fontWeight: 700,
            color: "var(--text-primary)",
            letterSpacing: "-0.02em",
            marginBottom: 4,
          }}
        >
          Strategic Intelligence Dashboard
        </h1>
        <p style={{ fontSize: 13, color: "var(--text-secondary)" }}>
          Board-level analysis powered by six specialised AI agents.
        </p>
      </motion.div>

      {/* Stat cards */}
      <motion.div
        variants={staggerContainer}
        initial="initial"
        animate="animate"
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(4, 1fr)",
          gap: 12,
          marginBottom: 28,
        }}
      >
        {stats.map(({ icon: Icon, label, value, sub }) => (
          <motion.div key={label} variants={staggerItem}>
            <Card hover padding="md">
              <div style={{ display: "flex", alignItems: "flex-start", gap: 12 }}>
                <div
                  style={{
                    width: 36,
                    height: 36,
                    borderRadius: "var(--radius-md)",
                    backgroundColor: "var(--accent-dim)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    flexShrink: 0,
                  }}
                >
                  <Icon size={16} style={{ color: "var(--accent)" }} />
                </div>
                <div>
                  <div
                    style={{
                      fontSize: 11,
                      color: "var(--text-tertiary)",
                      marginBottom: 2,
                      textTransform: "uppercase",
                      letterSpacing: "0.04em",
                    }}
                  >
                    {label}
                  </div>
                  <div
                    style={{
                      fontSize: 22,
                      fontWeight: 700,
                      color: "var(--text-primary)",
                      lineHeight: 1.1,
                    }}
                  >
                    {value}
                  </div>
                  <div
                    style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 2 }}
                  >
                    {sub}
                  </div>
                </div>
              </div>
            </Card>
          </motion.div>
        ))}
      </motion.div>

      {/* Recent analyses table */}
      <motion.div
        initial={fadeUp.initial}
        animate={fadeUp.animate}
        transition={{ ...fadeUp.transition, delay: 0.15 }}
      >
        <Card padding="none">
          {/* Table header */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              padding: "16px 20px",
              borderBottom: "1px solid var(--border)",
            }}
          >
            <span
              style={{
                fontSize: 13,
                fontWeight: 600,
                color: "var(--text-primary)",
              }}
            >
              Recent Analyses
            </span>
            <Link
              href="/reports"
              style={{
                fontSize: 12,
                color: "var(--accent)",
                textDecoration: "none",
                display: "flex",
                alignItems: "center",
                gap: 2,
              }}
            >
              View all
              <ChevronRight size={12} />
            </Link>
          </div>

          {/* Table content */}
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
                  margin: "0 auto 12px",
                }}
              />
              Loading analyses…
            </div>
          )}

          {error && (
            <div
              style={{
                padding: "48px 20px",
                textAlign: "center",
                color: "var(--danger)",
                fontSize: 13,
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                gap: 8,
              }}
            >
              <AlertCircle size={20} style={{ opacity: 0.7 }} />
              {error}
            </div>
          )}

          {!loading && !error && analyses.length === 0 && (
            <div
              style={{
                padding: "64px 20px",
                textAlign: "center",
              }}
            >
              <FileText
                size={32}
                style={{
                  color: "var(--text-tertiary)",
                  margin: "0 auto 12px",
                  display: "block",
                }}
              />
              <p
                style={{
                  color: "var(--text-secondary)",
                  fontSize: 13,
                  marginBottom: 16,
                }}
              >
                No analyses yet.
              </p>
              <Link
                href="/analysis/new"
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 6,
                  padding: "8px 16px",
                  backgroundColor: "var(--accent)",
                  color: "white",
                  borderRadius: "var(--radius-md)",
                  fontSize: 13,
                  fontWeight: 500,
                  textDecoration: "none",
                }}
              >
                <Plus size={14} />
                Start your first analysis
              </Link>
            </div>
          )}

          {!loading && analyses.length > 0 && (
            <div>
              {analyses.map((a, i) => (
                <Link
                  key={a.id}
                  href={`/analysis/${a.id}`}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    padding: "14px 20px",
                    borderBottom:
                      i < analyses.length - 1
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
                  {/* Status dot */}
                  <div style={{ marginRight: 12, flexShrink: 0 }}>
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
                    />
                  </div>

                  {/* Main content */}
                  <div style={{ flex: 1, minWidth: 0, marginRight: 16 }}>
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
                    <p
                      style={{
                        fontSize: 11,
                        color: "var(--text-tertiary)",
                        marginTop: 2,
                      }}
                    >
                      {formatDistanceToNow(new Date(a.created_at), {
                        addSuffix: true,
                      })}
                      {a.execution_time_ms != null && (
                        <span>
                          {" "}
                          · {(a.execution_time_ms / 1000).toFixed(0)}s
                        </span>
                      )}
                    </p>
                  </div>

                  {/* Right side */}
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 12,
                      flexShrink: 0,
                    }}
                  >
                    {a.confidence_score != null && (
                      <span
                        style={{
                          fontSize: 11,
                          color: "var(--text-tertiary)",
                          fontVariantNumeric: "tabular-nums",
                        }}
                      >
                        {a.confidence_score.toFixed(1)}/10
                      </span>
                    )}
                    <StatusBadge status={a.status} />
                    <ChevronRight
                      size={14}
                      style={{ color: "var(--text-tertiary)" }}
                    />
                  </div>
                </Link>
              ))}
            </div>
          )}
        </Card>
      </motion.div>
    </div>
  );
}

function avgScore(
  analyses: AnalysisSummary[],
  key: "confidence_score" | "data_quality_score"
): string {
  const scores = analyses
    .map((a) => a[key])
    .filter((s): s is number => s != null);
  if (!scores.length) return "—";
  return (scores.reduce((a, b) => a + b, 0) / scores.length).toFixed(1);
}

function avgDuration(analyses: AnalysisSummary[]): string {
  const times = analyses
    .map((a) => a.execution_time_ms)
    .filter((t): t is number => t != null);
  if (!times.length) return "—";
  const avg = times.reduce((a, b) => a + b, 0) / times.length;
  return `${(avg / 1000).toFixed(0)}s`;
}
