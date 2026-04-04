"use client";

/**
 * RiskMatrix — visual 5×5 severity/likelihood grid.
 * Renders using inline SVG (no charting lib dependency).
 * Colors reference CSS custom properties from the Railway dark design system.
 */

const LOW_COLOR = "#22C55E";
const MED_COLOR = "#F59E0B";
const HIGH_COLOR = "#EF4444";
const CRIT_COLOR = "#7f1d1d";

interface Cell {
  sx: number;
  sy: number;
  color: string;
  label: string;
}

const CELLS: Cell[] = [
  { sx: 1, sy: 1, color: LOW_COLOR, label: "Low" },
  { sx: 2, sy: 1, color: LOW_COLOR, label: "Low" },
  { sx: 3, sy: 1, color: MED_COLOR, label: "Med" },
  { sx: 4, sy: 1, color: MED_COLOR, label: "Med" },
  { sx: 5, sy: 1, color: HIGH_COLOR, label: "High" },
  { sx: 1, sy: 2, color: LOW_COLOR, label: "Low" },
  { sx: 2, sy: 2, color: MED_COLOR, label: "Med" },
  { sx: 3, sy: 2, color: MED_COLOR, label: "Med" },
  { sx: 4, sy: 2, color: HIGH_COLOR, label: "High" },
  { sx: 5, sy: 2, color: HIGH_COLOR, label: "High" },
  { sx: 1, sy: 3, color: MED_COLOR, label: "Med" },
  { sx: 2, sy: 3, color: MED_COLOR, label: "Med" },
  { sx: 3, sy: 3, color: HIGH_COLOR, label: "High" },
  { sx: 4, sy: 3, color: HIGH_COLOR, label: "High" },
  { sx: 5, sy: 3, color: CRIT_COLOR, label: "Crit" },
  { sx: 1, sy: 4, color: MED_COLOR, label: "Med" },
  { sx: 2, sy: 4, color: HIGH_COLOR, label: "High" },
  { sx: 3, sy: 4, color: HIGH_COLOR, label: "High" },
  { sx: 4, sy: 4, color: CRIT_COLOR, label: "Crit" },
  { sx: 5, sy: 4, color: CRIT_COLOR, label: "Crit" },
  { sx: 1, sy: 5, color: HIGH_COLOR, label: "High" },
  { sx: 2, sy: 5, color: HIGH_COLOR, label: "High" },
  { sx: 3, sy: 5, color: CRIT_COLOR, label: "Crit" },
  { sx: 4, sy: 5, color: CRIT_COLOR, label: "Crit" },
  { sx: 5, sy: 5, color: CRIT_COLOR, label: "Crit" },
];

const CELL_SIZE = 38;
const AXIS_OFFSET = 40;
const SVG_W = CELL_SIZE * 5 + AXIS_OFFSET + 12;
const SVG_H = CELL_SIZE * 5 + AXIS_OFFSET + 16;

export function RiskMatrix() {
  return (
    <div style={{ marginTop: 8 }}>
      <p
        style={{
          fontSize: 11,
          color: "var(--text-tertiary)",
          marginBottom: 8,
        }}
      >
        Risk Matrix (Severity × Likelihood)
      </p>

      <svg
        width={SVG_W}
        height={SVG_H}
        style={{ overflow: "visible" }}
        aria-label="Risk matrix chart"
      >
        {/* Axis labels */}
        <text
          x={10}
          y={(CELL_SIZE * 5 + AXIS_OFFSET) / 2}
          textAnchor="middle"
          fill="var(--text-tertiary)"
          fontSize={9}
          transform={`rotate(-90, 10, ${(CELL_SIZE * 5 + AXIS_OFFSET) / 2})`}
          fontFamily="var(--font-sans)"
        >
          Likelihood →
        </text>
        <text
          x={AXIS_OFFSET + (CELL_SIZE * 5) / 2}
          y={CELL_SIZE * 5 + AXIS_OFFSET + 12}
          textAnchor="middle"
          fill="var(--text-tertiary)"
          fontSize={9}
          fontFamily="var(--font-sans)"
        >
          Severity →
        </text>

        {/* Axis numbers */}
        {[1, 2, 3, 4, 5].map((v) => (
          <g key={v}>
            <text
              x={AXIS_OFFSET + (v - 1) * CELL_SIZE + CELL_SIZE / 2}
              y={AXIS_OFFSET - 6}
              textAnchor="middle"
              fill="var(--text-tertiary)"
              fontSize={8}
              fontFamily="var(--font-sans)"
            >
              {v}
            </text>
            <text
              x={AXIS_OFFSET - 8}
              y={AXIS_OFFSET + (5 - v) * CELL_SIZE + CELL_SIZE / 2 + 4}
              textAnchor="middle"
              fill="var(--text-tertiary)"
              fontSize={8}
              fontFamily="var(--font-sans)"
            >
              {v}
            </text>
          </g>
        ))}

        {/* Cells */}
        {CELLS.map(({ sx, sy, color }) => (
          <rect
            key={`${sx}-${sy}`}
            x={AXIS_OFFSET + (sx - 1) * CELL_SIZE + 1}
            y={AXIS_OFFSET + (5 - sy) * CELL_SIZE + 1}
            width={CELL_SIZE - 2}
            height={CELL_SIZE - 2}
            fill={`${color}26`}
            stroke={`${color}55`}
            strokeWidth={0.5}
            rx={2}
          />
        ))}
      </svg>

      {/* Legend */}
      <div style={{ display: "flex", gap: 14, marginTop: 8, flexWrap: "wrap" }}>
        {[
          { color: LOW_COLOR, label: "Low" },
          { color: MED_COLOR, label: "Medium" },
          { color: HIGH_COLOR, label: "High" },
          { color: CRIT_COLOR, label: "Critical" },
        ].map(({ color, label }) => (
          <div
            key={label}
            style={{ display: "flex", alignItems: "center", gap: 5 }}
          >
            <div
              style={{
                width: 11,
                height: 11,
                borderRadius: 2,
                backgroundColor: `${color}55`,
                border: `1px solid ${color}66`,
                flexShrink: 0,
              }}
            />
            <span
              style={{ fontSize: 11, color: "var(--text-tertiary)" }}
            >
              {label}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
