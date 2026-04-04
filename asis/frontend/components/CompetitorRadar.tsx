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

interface PorterDimension {
  subject: string;
  score: number;
  fullMark: number;
}

interface Props {
  data?: PorterDimension[];
  companyName?: string;
}

const DEFAULT_DATA: PorterDimension[] = [
  { subject: "Competitive Rivalry", score: 75, fullMark: 100 },
  { subject: "Supplier Power", score: 55, fullMark: 100 },
  { subject: "Buyer Power", score: 60, fullMark: 100 },
  { subject: "New Entrants", score: 45, fullMark: 100 },
  { subject: "Substitutes", score: 50, fullMark: 100 },
];

const TICK_STYLE = {
  fill: "var(--text-tertiary)",
  fontSize: 11,
  fontFamily: "var(--font-sans)",
};

export function CompetitorRadar({
  data = DEFAULT_DATA,
  companyName = "Market",
}: Props) {
  return (
    <div
      style={{
        backgroundColor: "var(--bg-surface)",
        border: "1px solid var(--border)",
        borderRadius: "var(--radius-lg)",
        padding: "16px 16px 8px",
      }}
    >
      <div style={{ marginBottom: 14 }}>
        <h4
          style={{
            fontSize: 13,
            fontWeight: 600,
            color: "var(--text-primary)",
            marginBottom: 2,
          }}
        >
          Porter's Five Forces
        </h4>
        <p style={{ fontSize: 11, color: "var(--text-tertiary)" }}>
          Competitive intensity analysis for {companyName}
        </p>
      </div>

      <ResponsiveContainer width="100%" height={280}>
        <RadarChart data={data} margin={{ top: 8, right: 24, bottom: 8, left: 24 }}>
          <PolarGrid
            stroke="var(--border)"
            strokeOpacity={0.6}
          />
          <PolarAngleAxis
            dataKey="subject"
            tick={TICK_STYLE}
            stroke="var(--border)"
          />
          <Radar
            name="Force Intensity"
            dataKey="score"
            stroke="var(--accent)"
            fill="var(--accent)"
            fillOpacity={0.18}
            strokeWidth={2}
            dot={{
              fill: "var(--accent)",
              r: 3,
              strokeWidth: 0,
            }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "var(--bg-elevated)",
              border: "1px solid var(--border)",
              borderRadius: "var(--radius-md)",
              fontSize: 12,
              color: "var(--text-primary)",
              boxShadow: "var(--shadow-md)",
            }}
            itemStyle={{ color: "var(--accent)" }}
            formatter={(value: number) => [`${value}/100`, "Force Intensity"]}
          />
          <Legend
            wrapperStyle={{ fontSize: 11, color: "var(--text-secondary)", paddingTop: 8 }}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
