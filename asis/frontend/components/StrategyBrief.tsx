"use client";

import { motion } from "framer-motion";
import { slideUp } from "@/lib/animations";
import type { StrategicBrief } from "@/lib/api";
import { ExportControls } from "./ExportControls";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import {
  CheckCircle2,
  AlertTriangle,
  TrendingUp,
  Target,
  BarChart3,
  Download,
  BookOpen,
} from "lucide-react";

interface Props {
  brief: StrategicBrief;
  analysisId: string;
}

const DECISION_CONFIG: Record<
  string,
  { color: string; bg: string; border: string; variant: "success" | "warning" | "danger" | "accent" }
> = {
  PROCEED: { color: "var(--success)", bg: "rgba(34,197,94,0.06)", border: "rgba(34,197,94,0.3)", variant: "success" },
  DEFER: { color: "var(--warning)", bg: "rgba(245,158,11,0.06)", border: "rgba(245,158,11,0.3)", variant: "warning" },
  REJECT: { color: "var(--danger)", bg: "rgba(239,68,68,0.06)", border: "rgba(239,68,68,0.3)", variant: "danger" },
  CONDITIONAL: { color: "var(--accent)", bg: "var(--accent-dim)", border: "rgba(124,58,237,0.35)", variant: "accent" },
};

export function StrategyBrief({ brief, analysisId }: Props) {
  const decision = brief.decision_recommendation ?? "CONDITIONAL";
  const dc = DECISION_CONFIG[decision] ?? DECISION_CONFIG.CONDITIONAL;
  const confidence = brief.overall_confidence ?? 0;
  const confColor =
    confidence >= 75 ? "var(--success)" : confidence >= 50 ? "var(--warning)" : "var(--danger)";

  return (
    <motion.div
      initial={slideUp.initial}
      animate={slideUp.animate}
      transition={slideUp.transition}
      style={{ display: "flex", flexDirection: "column", gap: 12 }}
    >
      {/* Board Narrative Banner */}
      <div
        style={{
          padding: "18px 20px",
          borderRadius: "var(--radius-lg)",
          backgroundColor: dc.bg,
          border: `1px solid ${dc.border}`,
        }}
      >
        <div style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
          <Target size={16} style={{ color: dc.color, flexShrink: 0, marginTop: 2 }} />
          <div style={{ flex: 1 }}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 10,
                marginBottom: 8,
              }}
            >
              <p
                style={{
                  fontSize: 10,
                  fontWeight: 700,
                  color: dc.color,
                  textTransform: "uppercase",
                  letterSpacing: "0.06em",
                }}
              >
                Board Decision
              </p>
              <Badge variant={dc.variant}>{decision}</Badge>
            </div>
            <p
              style={{
                fontSize: 14,
                fontWeight: 500,
                color: "var(--text-primary)",
                lineHeight: 1.55,
                fontStyle: "italic",
              }}
            >
              &ldquo;{brief.board_narrative}&rdquo;
            </p>
          </div>
          {/* Confidence dial */}
          <div
            style={{
              flexShrink: 0,
              textAlign: "center",
              padding: "8px 14px",
              borderRadius: "var(--radius-md)",
              border: "1px solid var(--border)",
              backgroundColor: "var(--bg-surface)",
            }}
          >
            <p
              style={{
                fontSize: 22,
                fontWeight: 700,
                color: confColor,
                lineHeight: 1,
                fontVariantNumeric: "tabular-nums",
              }}
            >
              {confidence}
              <span style={{ fontSize: 11, fontWeight: 400, color: "var(--text-tertiary)" }}>
                /100
              </span>
            </p>
            <p style={{ fontSize: 9, color: "var(--text-tertiary)", marginTop: 3, textTransform: "uppercase", letterSpacing: "0.05em" }}>
              Confidence
            </p>
          </div>
        </div>
      </div>

      {/* Executive Summary */}
      <Section title="Executive Summary" icon={<TrendingUp size={14} />}>
        <p
          style={{
            fontSize: 13,
            color: "var(--text-secondary)",
            lineHeight: 1.75,
            whiteSpace: "pre-wrap",
          }}
        >
          {brief.executive_summary}
        </p>
      </Section>

      {/* Strategic Imperatives */}
      <Section title="Strategic Imperatives" icon={<Target size={14} />}>
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {(brief.strategic_imperatives ?? []).map((imp, i) => (
            <div
              key={i}
              style={{
                display: "flex",
                gap: 10,
                padding: "10px 14px",
                borderRadius: "var(--radius-md)",
                backgroundColor: "var(--bg-elevated)",
                border: "1px solid var(--border)",
              }}
            >
              <span
                style={{
                  width: 20,
                  height: 20,
                  borderRadius: "50%",
                  backgroundColor: "var(--accent)",
                  color: "white",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: 10,
                  fontWeight: 700,
                  flexShrink: 0,
                  marginTop: 1,
                }}
              >
                {i + 1}
              </span>
              <p style={{ fontSize: 13, color: "var(--text-primary)", lineHeight: 1.5 }}>
                {imp}
              </p>
            </div>
          ))}
        </div>
      </Section>

      {/* Phased Roadmap */}
      <Section title="Strategic Roadmap" icon={<BarChart3 size={14} />}>
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {(brief.roadmap ?? []).map((phase, i) => (
            <div
              key={i}
              style={{
                padding: "14px 16px",
                borderRadius: "var(--radius-md)",
                border: i === 0 ? "1px solid rgba(124,58,237,0.4)" : "1px solid var(--border)",
                backgroundColor: i === 0 ? "var(--accent-dim)" : "var(--bg-elevated)",
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  marginBottom: 6,
                }}
              >
                <p style={{ fontSize: 12, fontWeight: 700, color: "var(--text-primary)" }}>
                  {phase.phase}
                </p>
                <span
                  style={{
                    fontSize: 11,
                    fontWeight: 600,
                    color: "var(--accent)",
                    fontFamily: "var(--font-mono)",
                  }}
                >
                  {phase.investment}
                </span>
              </div>
              <p style={{ fontSize: 12, color: "var(--text-secondary)", marginBottom: 8, lineHeight: 1.4 }}>
                {phase.focus}
              </p>
              <ul style={{ display: "flex", flexDirection: "column", gap: 4, marginBottom: 8 }}>
                {(phase.key_actions ?? []).map((action, j) => (
                  <li
                    key={j}
                    style={{
                      display: "flex",
                      gap: 6,
                      alignItems: "flex-start",
                      fontSize: 12,
                      color: "var(--text-secondary)",
                    }}
                  >
                    <CheckCircle2
                      size={11}
                      style={{ color: "var(--success)", flexShrink: 0, marginTop: 2 }}
                    />
                    {action}
                  </li>
                ))}
              </ul>
              <p
                style={{
                  fontSize: 11,
                  color: "var(--text-tertiary)",
                  fontStyle: "italic",
                  borderTop: "1px solid var(--border)",
                  paddingTop: 6,
                }}
              >
                KPI: {phase.success_metric}
              </p>
            </div>
          ))}
        </div>
      </Section>

      {/* Balanced Scorecard */}
      {brief.balanced_scorecard && (
        <Section title="Balanced Scorecard" icon={<BarChart3 size={14} />}>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: 8,
            }}
          >
            {[
              { label: "Financial", key: "financial", color: "var(--success)" },
              { label: "Customer", key: "customer", color: "var(--accent)" },
              { label: "Internal Process", key: "internal_process", color: "var(--warning)" },
              { label: "Learning & Growth", key: "learning_growth", color: "#60a5fa" },
            ].map(({ label, key, color }) => (
              <div
                key={key}
                style={{
                  padding: "12px 14px",
                  borderRadius: "var(--radius-md)",
                  backgroundColor: "var(--bg-elevated)",
                  border: "1px solid var(--border)",
                }}
              >
                <p
                  style={{
                    fontSize: 10,
                    fontWeight: 700,
                    color,
                    textTransform: "uppercase",
                    letterSpacing: "0.05em",
                    marginBottom: 6,
                  }}
                >
                  {label}
                </p>
                <p style={{ fontSize: 12, color: "var(--text-secondary)", lineHeight: 1.5 }}>
                  {brief.balanced_scorecard[key as keyof typeof brief.balanced_scorecard]}
                </p>
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* Success Metrics */}
      {(brief.success_metrics ?? []).length > 0 && (
        <Section title="Success Metrics" icon={<CheckCircle2 size={14} />}>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {brief.success_metrics.map((metric, i) => (
              <div
                key={i}
                style={{
                  display: "flex",
                  gap: 8,
                  alignItems: "flex-start",
                  padding: "8px 12px",
                  borderRadius: "var(--radius-md)",
                  backgroundColor: "var(--bg-elevated)",
                  border: "1px solid var(--border)",
                }}
              >
                <AlertTriangle
                  size={11}
                  style={{ color: "var(--warning)", flexShrink: 0, marginTop: 2 }}
                />
                <p style={{ fontSize: 12, color: "var(--text-secondary)", lineHeight: 1.45 }}>
                  {metric}
                </p>
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* Dissertation Contribution */}
      {brief.dissertation_contribution && (
        <div
          style={{
            padding: "12px 16px",
            borderRadius: "var(--radius-lg)",
            border: "1px solid var(--border)",
            backgroundColor: "var(--bg-elevated)",
            display: "flex",
            gap: 10,
            alignItems: "flex-start",
          }}
        >
          <BookOpen size={13} style={{ color: "var(--text-tertiary)", flexShrink: 0, marginTop: 1 }} />
          <p
            style={{
              fontSize: 11,
              color: "var(--text-tertiary)",
              lineHeight: 1.6,
              fontStyle: "italic",
            }}
          >
            {brief.dissertation_contribution}
          </p>
        </div>
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
