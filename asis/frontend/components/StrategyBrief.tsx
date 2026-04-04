"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { slideUp } from "@/lib/animations";
import type { StrategicBrief } from "@/lib/api";
import { ExportControls } from "./ExportControls";
import { RiskMatrix } from "./RiskMatrix";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import {
  CheckCircle2,
  AlertTriangle,
  TrendingUp,
  Target,
  ChevronDown,
  ChevronUp,
  Download,
} from "lucide-react";

interface Props {
  brief: StrategicBrief;
  analysisId: string;
}

export function StrategyBrief({ brief, analysisId }: Props) {
  const [showSources, setShowSources] = useState(false);

  return (
    <motion.div
      initial={slideUp.initial}
      animate={slideUp.animate}
      transition={slideUp.transition}
      style={{ display: "flex", flexDirection: "column", gap: 12 }}
    >
      {/* Recommendation Banner */}
      <div
        style={{
          padding: "18px 20px",
          borderRadius: "var(--radius-lg)",
          backgroundColor: "var(--accent-dim)",
          border: "1px solid rgba(124,58,237,0.35)",
        }}
      >
        <div style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
          <Target
            size={16}
            style={{ color: "var(--accent)", flexShrink: 0, marginTop: 2 }}
          />
          <div>
            <p
              style={{
                fontSize: 10,
                fontWeight: 700,
                color: "var(--accent)",
                textTransform: "uppercase",
                letterSpacing: "0.06em",
                marginBottom: 6,
              }}
            >
              Lead Recommendation
            </p>
            <p
              style={{
                fontSize: 14,
                fontWeight: 500,
                color: "var(--text-primary)",
                lineHeight: 1.55,
              }}
            >
              {brief.recommendation}
            </p>
          </div>
        </div>
      </div>

      {/* Score grid */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
        <ScoreCard label="Confidence Score" score={brief.confidence_score} />
        <ScoreCard label="Data Quality" score={brief.data_quality_score} />
      </div>

      {/* Executive Summary */}
      <Section title="Executive Summary" icon={<TrendingUp size={14} />}>
        <p
          style={{
            fontSize: 13,
            color: "var(--text-secondary)",
            lineHeight: 1.7,
            whiteSpace: "pre-wrap",
          }}
        >
          {brief.executive_summary}
        </p>
      </Section>

      {/* Strategic Options */}
      <Section title="Strategic Options" icon={<Target size={14} />}>
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {brief.strategic_options.map((opt, index) => (
            <div
              key={opt.option_id}
              style={{
                padding: "14px 16px",
                borderRadius: "var(--radius-md)",
                border: opt.recommended
                  ? "1px solid rgba(124,58,237,0.4)"
                  : "1px solid var(--border)",
                backgroundColor: opt.recommended
                  ? "var(--accent-dim)"
                  : "var(--bg-elevated)",
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "flex-start",
                  justifyContent: "space-between",
                  gap: 8,
                  marginBottom: 8,
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span
                    style={{
                      width: 20,
                      height: 20,
                      borderRadius: "50%",
                      backgroundColor: opt.recommended
                        ? "var(--accent)"
                        : "var(--bg-overlay)",
                      color: opt.recommended ? "white" : "var(--text-tertiary)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: 10,
                      fontWeight: 700,
                      flexShrink: 0,
                    }}
                  >
                    {index + 1}
                  </span>
                  <p
                    style={{
                      fontSize: 13,
                      fontWeight: 600,
                      color: "var(--text-primary)",
                    }}
                  >
                    {opt.title}
                  </p>
                </div>
                <div style={{ display: "flex", gap: 6, flexShrink: 0 }}>
                  {opt.recommended && (
                    <Badge variant="accent">Recommended</Badge>
                  )}
                  <RiskLevelBadge level={opt.risk_level} />
                </div>
              </div>

              <p
                style={{
                  fontSize: 12,
                  color: "var(--text-secondary)",
                  marginBottom: 10,
                  lineHeight: 1.5,
                }}
              >
                {opt.description}
              </p>

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr",
                  gap: 10,
                }}
              >
                <div>
                  <p
                    style={{
                      fontSize: 10,
                      fontWeight: 600,
                      color: "var(--success)",
                      textTransform: "uppercase",
                      letterSpacing: "0.04em",
                      marginBottom: 4,
                    }}
                  >
                    Pros
                  </p>
                  <ul style={{ display: "flex", flexDirection: "column", gap: 3 }}>
                    {opt.pros.map((p, i) => (
                      <li
                        key={i}
                        style={{
                          display: "flex",
                          gap: 6,
                          alignItems: "flex-start",
                          fontSize: 11,
                          color: "var(--text-secondary)",
                        }}
                      >
                        <CheckCircle2
                          size={10}
                          style={{
                            color: "var(--success)",
                            flexShrink: 0,
                            marginTop: 2,
                          }}
                        />
                        {p}
                      </li>
                    ))}
                  </ul>
                </div>
                <div>
                  <p
                    style={{
                      fontSize: 10,
                      fontWeight: 600,
                      color: "var(--warning)",
                      textTransform: "uppercase",
                      letterSpacing: "0.04em",
                      marginBottom: 4,
                    }}
                  >
                    Cons
                  </p>
                  <ul style={{ display: "flex", flexDirection: "column", gap: 3 }}>
                    {opt.cons.map((c, i) => (
                      <li
                        key={i}
                        style={{
                          display: "flex",
                          gap: 6,
                          alignItems: "flex-start",
                          fontSize: 11,
                          color: "var(--text-secondary)",
                        }}
                      >
                        <AlertTriangle
                          size={10}
                          style={{
                            color: "var(--warning)",
                            flexShrink: 0,
                            marginTop: 2,
                          }}
                        />
                        {c}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>

              {(opt.estimated_investment_usd_mn != null || opt.time_to_value) && (
                <p
                  style={{
                    fontSize: 11,
                    color: "var(--text-tertiary)",
                    marginTop: 8,
                    fontFamily: "var(--font-mono)",
                  }}
                >
                  {opt.estimated_investment_usd_mn != null &&
                    `Est. investment: $${opt.estimated_investment_usd_mn}M`}
                  {opt.time_to_value ? ` · ${opt.time_to_value}` : ""}
                </p>
              )}
            </div>
          ))}
        </div>
      </Section>

      {/* Risk Assessment */}
      <Section title="Risk Assessment" icon={<AlertTriangle size={14} />}>
        <p
          style={{
            fontSize: 13,
            color: "var(--text-secondary)",
            lineHeight: 1.65,
            marginBottom: 12,
          }}
        >
          {brief.risk_summary}
        </p>
        <RiskMatrix />
      </Section>

      {/* Financial Summary — 3-col grid */}
      <Section title="Financial Considerations" icon={<TrendingUp size={14} />}>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(3, 1fr)",
            gap: 10,
            marginBottom: 12,
          }}
        >
          {[
            { label: "Market Opportunity", value: "See brief" },
            { label: "Est. Investment", value: "Variable" },
            { label: "Risk-Adj. Return", value: "TBD" },
          ].map(({ label, value }) => (
            <div
              key={label}
              style={{
                padding: "10px 12px",
                backgroundColor: "var(--bg-elevated)",
                borderRadius: "var(--radius-md)",
                border: "1px solid var(--border)",
              }}
            >
              <p
                style={{
                  fontSize: 10,
                  color: "var(--text-tertiary)",
                  marginBottom: 4,
                  textTransform: "uppercase",
                  letterSpacing: "0.04em",
                }}
              >
                {label}
              </p>
              <p
                style={{
                  fontSize: 13,
                  fontWeight: 600,
                  color: "var(--text-primary)",
                }}
              >
                {value}
              </p>
            </div>
          ))}
        </div>
        <p
          style={{
            fontSize: 13,
            color: "var(--text-secondary)",
            lineHeight: 1.65,
          }}
        >
          {brief.financial_summary}
        </p>
      </Section>

      {/* Next Steps checklist */}
      <Section title="Next Steps" icon={<CheckCircle2 size={14} />}>
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {brief.next_steps
            .slice()
            .sort((a, b) => a.priority - b.priority)
            .map((step, i) => (
              <div
                key={i}
                style={{
                  display: "flex",
                  gap: 12,
                  padding: "12px 14px",
                  backgroundColor: "var(--bg-elevated)",
                  borderRadius: "var(--radius-md)",
                  border: "1px solid var(--border)",
                }}
              >
                <div
                  style={{
                    width: 22,
                    height: 22,
                    borderRadius: "50%",
                    backgroundColor: "var(--accent-dim)",
                    border: "1px solid rgba(124,58,237,0.3)",
                    color: "var(--accent)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontSize: 10,
                    fontWeight: 700,
                    flexShrink: 0,
                  }}
                >
                  {step.priority}
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <p
                    style={{
                      fontSize: 13,
                      fontWeight: 500,
                      color: "var(--text-primary)",
                    }}
                  >
                    {step.action}
                  </p>
                  <p
                    style={{
                      fontSize: 11,
                      color: "var(--text-tertiary)",
                      marginTop: 2,
                    }}
                  >
                    {step.owner} · {step.timeline}
                  </p>
                  {step.success_criteria && (
                    <p
                      style={{
                        fontSize: 11,
                        color: "var(--text-tertiary)",
                        marginTop: 2,
                        fontStyle: "italic",
                      }}
                    >
                      {step.success_criteria}
                    </p>
                  )}
                </div>
              </div>
            ))}
        </div>
      </Section>

      {/* Caveats */}
      {brief.caveats.length > 0 && (
        <div
          style={{
            padding: "14px 16px",
            borderRadius: "var(--radius-lg)",
            border: "1px solid rgba(245,158,11,0.3)",
            backgroundColor: "rgba(245,158,11,0.06)",
          }}
        >
          <p
            style={{
              fontSize: 11,
              fontWeight: 600,
              color: "var(--warning)",
              textTransform: "uppercase",
              letterSpacing: "0.05em",
              marginBottom: 8,
            }}
          >
            Caveats
          </p>
          <ul style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            {brief.caveats.map((c, i) => (
              <li
                key={i}
                style={{ fontSize: 12, color: "var(--text-secondary)" }}
              >
                {c}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Sources footer */}
      {brief.sources.length > 0 && (
        <Card padding="md">
          <button
            type="button"
            onClick={() => setShowSources((s) => !s)}
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              width: "100%",
              background: "none",
              border: "none",
              cursor: "pointer",
              padding: 0,
            }}
          >
            <span
              style={{
                fontSize: 12,
                fontWeight: 500,
                color: "var(--text-secondary)",
              }}
            >
              Sources ({brief.sources.length})
            </span>
            {showSources ? (
              <ChevronUp size={13} style={{ color: "var(--text-tertiary)" }} />
            ) : (
              <ChevronDown size={13} style={{ color: "var(--text-tertiary)" }} />
            )}
          </button>
          {showSources && (
            <ul
              style={{
                marginTop: 10,
                display: "flex",
                flexDirection: "column",
                gap: 3,
              }}
            >
              {brief.sources.map((src, i) => (
                <li
                  key={i}
                  style={{ fontSize: 11, color: "var(--text-tertiary)" }}
                >
                  [{i + 1}] {src}
                </li>
              ))}
            </ul>
          )}
        </Card>
      )}

      {/* Sticky export bar */}
      <div
        style={{
          position: "sticky",
          bottom: 16,
          display: "flex",
          justifyContent: "flex-end",
          pointerEvents: "none",
        }}
      >
        <div
          style={{
            pointerEvents: "all",
            backgroundColor: "var(--bg-surface)",
            border: "1px solid var(--border)",
            borderRadius: "var(--radius-lg)",
            padding: "8px 12px",
            display: "flex",
            alignItems: "center",
            gap: 8,
            boxShadow: "var(--shadow-md)",
          }}
        >
          <Download size={14} style={{ color: "var(--text-tertiary)" }} />
          <ExportControls brief={brief} analysisId={analysisId} />
        </div>
      </div>
    </motion.div>
  );
}

/* ─── Sub-components ─────────────────────────────────────────────────────── */

function Section({
  title,
  icon,
  children,
}: {
  title: string;
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <Card padding="md">
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          marginBottom: 12,
          paddingBottom: 10,
          borderBottom: "1px solid var(--border)",
        }}
      >
        <span style={{ color: "var(--accent)" }}>{icon}</span>
        <h4
          style={{
            fontSize: 13,
            fontWeight: 600,
            color: "var(--text-primary)",
          }}
        >
          {title}
        </h4>
      </div>
      {children}
    </Card>
  );
}

function ScoreCard({ label, score }: { label: string; score: number }) {
  const isHigh = score >= 7.5;
  const isMid = score >= 5;
  const color = isHigh
    ? "var(--success)"
    : isMid
    ? "var(--warning)"
    : "var(--danger)";
  const bg = isHigh
    ? "rgba(34,197,94,0.06)"
    : isMid
    ? "rgba(245,158,11,0.06)"
    : "rgba(239,68,68,0.06)";
  const border = isHigh
    ? "rgba(34,197,94,0.2)"
    : isMid
    ? "rgba(245,158,11,0.2)"
    : "rgba(239,68,68,0.2)";

  return (
    <div
      style={{
        padding: "12px 14px",
        borderRadius: "var(--radius-md)",
        border: `1px solid ${border}`,
        backgroundColor: bg,
      }}
    >
      <p style={{ fontSize: 11, color: "var(--text-tertiary)", marginBottom: 4 }}>
        {label}
      </p>
      <p
        style={{
          fontSize: 22,
          fontWeight: 700,
          color,
          fontVariantNumeric: "tabular-nums",
          lineHeight: 1,
        }}
      >
        {score.toFixed(1)}
        <span
          style={{
            fontSize: 12,
            fontWeight: 400,
            color: "var(--text-tertiary)",
          }}
        >
          /10
        </span>
      </p>
    </div>
  );
}

function RiskLevelBadge({ level }: { level: string }) {
  const variant =
    level === "low" ? "success" : level === "medium" ? "warning" : "danger";
  return (
    <Badge variant={variant as "success" | "warning" | "danger"}>
      {level}
    </Badge>
  );
}
