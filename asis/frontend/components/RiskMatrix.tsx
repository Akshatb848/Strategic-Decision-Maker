"use client";

/**
 * RiskMatrix — visual 5×5 severity/likelihood grid.
 * Renders using inline SVG (no charting lib dependency).
 */
export function RiskMatrix() {
  const cells: Array<{ sx: number; sy: number; color: string; label: string }> = [
    // Risk matrix quadrants (severity × likelihood, 1-indexed)
    { sx: 1, sy: 1, color: "#16a34a", label: "Low" },
    { sx: 2, sy: 1, color: "#16a34a", label: "Low" },
    { sx: 3, sy: 1, color: "#ca8a04", label: "Med" },
    { sx: 4, sy: 1, color: "#ca8a04", label: "Med" },
    { sx: 5, sy: 1, color: "#dc2626", label: "High" },
    { sx: 1, sy: 2, color: "#16a34a", label: "Low" },
    { sx: 2, sy: 2, color: "#ca8a04", label: "Med" },
    { sx: 3, sy: 2, color: "#ca8a04", label: "Med" },
    { sx: 4, sy: 2, color: "#dc2626", label: "High" },
    { sx: 5, sy: 2, color: "#dc2626", label: "High" },
    { sx: 1, sy: 3, color: "#ca8a04", label: "Med" },
    { sx: 2, sy: 3, color: "#ca8a04", label: "Med" },
    { sx: 3, sy: 3, color: "#dc2626", label: "High" },
    { sx: 4, sy: 3, color: "#dc2626", label: "High" },
    { sx: 5, sy: 3, color: "#7f1d1d", label: "Crit" },
    { sx: 1, sy: 4, color: "#ca8a04", label: "Med" },
    { sx: 2, sy: 4, color: "#dc2626", label: "High" },
    { sx: 3, sy: 4, color: "#dc2626", label: "High" },
    { sx: 4, sy: 4, color: "#7f1d1d", label: "Crit" },
    { sx: 5, sy: 4, color: "#7f1d1d", label: "Crit" },
    { sx: 1, sy: 5, color: "#dc2626", label: "High" },
    { sx: 2, sy: 5, color: "#dc2626", label: "High" },
    { sx: 3, sy: 5, color: "#7f1d1d", label: "Crit" },
    { sx: 4, sy: 5, color: "#7f1d1d", label: "Crit" },
    { sx: 5, sy: 5, color: "#7f1d1d", label: "Crit" },
  ];

  const CELL = 40;
  const OFFSET = 40;

  return (
    <div className="mt-2">
      <p className="text-gray-500 text-xs mb-2">Risk Matrix (Severity × Likelihood)</p>
      <svg
        width={CELL * 5 + OFFSET + 10}
        height={CELL * 5 + OFFSET + 10}
        className="text-xs"
      >
        {/* Y axis label */}
        <text
          x={10}
          y={(CELL * 5 + OFFSET) / 2}
          textAnchor="middle"
          fill="#6b7280"
          fontSize={10}
          transform={`rotate(-90, 10, ${(CELL * 5 + OFFSET) / 2})`}
        >
          Likelihood →
        </text>
        {/* X axis label */}
        <text
          x={OFFSET + (CELL * 5) / 2}
          y={CELL * 5 + OFFSET + 8}
          textAnchor="middle"
          fill="#6b7280"
          fontSize={10}
        >
          Severity →
        </text>

        {/* Grid labels */}
        {[1, 2, 3, 4, 5].map((v) => (
          <g key={v}>
            <text x={OFFSET + (v - 1) * CELL + CELL / 2} y={OFFSET - 6} textAnchor="middle" fill="#4b5563" fontSize={9}>
              {v}
            </text>
            <text x={OFFSET - 8} y={OFFSET + (5 - v) * CELL + CELL / 2 + 4} textAnchor="middle" fill="#4b5563" fontSize={9}>
              {v}
            </text>
          </g>
        ))}

        {/* Cells */}
        {cells.map(({ sx, sy, color }) => (
          <rect
            key={`${sx}-${sy}`}
            x={OFFSET + (sx - 1) * CELL + 1}
            y={OFFSET + (5 - sy) * CELL + 1}
            width={CELL - 2}
            height={CELL - 2}
            fill={`${color}33`}
            stroke={`${color}66`}
            strokeWidth={0.5}
            rx={2}
          />
        ))}
      </svg>

      {/* Legend */}
      <div className="flex gap-4 mt-2">
        {[
          { color: "#16a34a", label: "Low" },
          { color: "#ca8a04", label: "Medium" },
          { color: "#dc2626", label: "High" },
          { color: "#7f1d1d", label: "Critical" },
        ].map(({ color, label }) => (
          <div key={label} className="flex items-center gap-1.5">
            <div className="w-3 h-3 rounded-sm" style={{ backgroundColor: `${color}66` }} />
            <span className="text-gray-500 text-xs">{label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
