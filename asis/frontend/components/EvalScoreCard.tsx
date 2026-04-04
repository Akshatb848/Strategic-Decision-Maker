"use client";

import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  Radar,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import type { EvaluationResponse } from "@/lib/api";

interface Props {
  evaluation: EvaluationResponse;
}

interface RadarDatum {
  dimension: string;
  score: number;
  baseline: number;
  fullMark: number;
}

function evalToRadarData(ev: EvaluationResponse): RadarDatum[] {
  return [
    {
      dimension: "Analytical Depth",
      score: ev.analytical_depth ?? 0,
      baseline: ev.baseline_overall_score ?? 0,
      fullMark: 10,
    },
    {
      dimension: "Factual Accuracy",
      score: ev.factual_accuracy ?? 0,
      baseline: ev.baseline_overall_score ?? 0,
      fullMark: 10,
    },
    {
      dimension: "Contextual Relevance",
      score: ev.contextual_relevance ?? 0,
      baseline: ev.baseline_overall_score ?? 0,
      fullMark: 10,
    },
    {
      dimension: "Actionability",
      score: ev.actionability ?? 0,
      baseline: ev.baseline_overall_score ?? 0,
      fullMark: 10,
    },
    {
      dimension: "Internal Consistency",
      score: ev.internal_consistency ?? 0,
      baseline: ev.baseline_overall_score ?? 0,
      fullMark: 10,
    },
  ];
}

const TICK_STYLE = {
  fill: "var(--text-tertiary)",
  fontSize: 10,
  fontFamily: "var(--font-sans)",
};

export function EvalScoreCard({ evaluation }: Props) {
  const data = evalToRadarData(evaluation);
  const hasBaseline = evaluation.baseline_overall_score != null;
  const improvement = evaluation.improvement_over_baseline;

  return (
    <div
      style={{
        backgroundColor: "var(--bg-surface)",
        border: "1px solid var(--border)",
        borderRadius: "var(--radius-lg)",
        padding: "16px 16px 8px",
      }}
    >
      {/* Header */}
      <div
        style={{
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "space-between",
          marginBottom: 14,
        }}
      >
        <div>
          <h4
            style={{
              fontSize: 13,
              fontWeight: 600,
              color: "var(--text-primary)",
              marginBottom: 2,
            }}
          >
            Evaluation Scorecard
          </h4>
          <p style={{ fontSize: 11, color: "var(--text-tertiary)" }}>
            Multi-agent vs baseline comparison
          </p>
        </div>
        {improvement != null && (
          <div
            style={{
              padding: "4px 8px",
              borderRadius: "var(--radius-sm)",
              backgroundColor:
                improvement > 0 ? "var(--success-dim)" : "var(--danger-dim)",
              border: `1px solid ${improvement > 0 ? "rgba(34,197,94,0.25)" : "rgba(239,68,68,0.25)"}`,
            }}
          >
            <span
              style={{
                fontSize: 11,
                fontWeight: 700,
                color: improvement > 0 ? "var(--success)" : "var(--danger)",
              }}
            >
              {improvement > 0 ? "+" : ""}
              {improvement.toFixed(1)} vs baseline
            </span>
          </div>
        )}
      </div>

      {/* Overall score */}
      {evaluation.overall_score != null && (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: hasBaseline ? "1fr 1fr" : "1fr",
            gap: 8,
            marginBottom: 14,
          }}
        >
          <ScoreChip label="Multi-Agent" value={evaluation.overall_score} color="var(--accent)" />
          {hasBaseline && evaluation.baseline_overall_score != null && (
            <ScoreChip
              label="Baseline"
              value={evaluation.baseline_overall_score}
              color="var(--text-tertiary)"
            />
          )}
        </div>
      )}

      {/* Radar */}
      <ResponsiveContainer width="100%" height={260}>
        <RadarChart data={data} margin={{ top: 8, right: 28, bottom: 8, left: 28 }}>
          <PolarGrid stroke="var(--border)" strokeOpacity={0.6} />
          <PolarAngleAxis dataKey="dimension" tick={TICK_STYLE} stroke="var(--border)" />
          <Radar
            name="Multi-Agent"
            dataKey="score"
            stroke="var(--accent)"
            fill="var(--accent)"
            fillOpacity={0.2}
            strokeWidth={2}
          />
          {hasBaseline && (
            <Radar
              name="Baseline"
              dataKey="baseline"
              stroke="var(--text-tertiary)"
              fill="var(--text-tertiary)"
              fillOpacity={0.08}
              strokeWidth={1.5}
              strokeDasharray="4 3"
            />
          )}
          <Tooltip
            contentStyle={{
              backgroundColor: "var(--bg-elevated)",
              border: "1px solid var(--border)",
              borderRadius: "var(--radius-md)",
              fontSize: 12,
              color: "var(--text-primary)",
              boxShadow: "var(--shadow-md)",
            }}
            formatter={(value: number) => [`${value.toFixed(1)}/10`]}
          />
          <Legend
            wrapperStyle={{
              fontSize: 11,
              color: "var(--text-secondary)",
              paddingTop: 8,
            }}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}

function ScoreChip({
  label,
  value,
  color,
}: {
  label: string;
  value: number;
  color: string;
}) {
  return (
    <div
      style={{
        padding: "8px 10px",
        borderRadius: "var(--radius-md)",
        border: "1px solid var(--border)",
        backgroundColor: "var(--bg-elevated)",
        textAlign: "center",
      }}
    >
      <p
        style={{
          fontSize: 10,
          color: "var(--text-tertiary)",
          textTransform: "uppercase",
          letterSpacing: "0.04em",
          marginBottom: 4,
        }}
      >
        {label}
      </p>
      <p style={{ fontSize: 20, fontWeight: 700, color }}>
        {value.toFixed(1)}
        <span style={{ fontSize: 11, fontWeight: 400, color: "var(--text-tertiary)" }}>
          /10
        </span>
      </p>
    </div>
  );
}
