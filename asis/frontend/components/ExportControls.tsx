"use client";

import type { StrategicBrief } from "@/lib/api";
import { Download, FileText } from "lucide-react";

interface Props {
  brief: StrategicBrief;
  analysisId: string;
}

export function ExportControls({ brief, analysisId }: Props) {
  const exportJSON = () => {
    const blob = new Blob([JSON.stringify(brief, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `asis-report-${analysisId.slice(0, 8)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const exportMarkdown = () => {
    const md = briefToMarkdown(brief, analysisId);
    const blob = new Blob([md], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `asis-report-${analysisId.slice(0, 8)}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="flex items-center gap-2">
      <button
        onClick={exportMarkdown}
        className="btn-secondary flex items-center gap-1.5 text-xs py-1.5 px-3"
      >
        <FileText size={13} />
        Export MD
      </button>
      <button
        onClick={exportJSON}
        className="btn-secondary flex items-center gap-1.5 text-xs py-1.5 px-3"
      >
        <Download size={13} />
        Export JSON
      </button>
    </div>
  );
}

function briefToMarkdown(brief: StrategicBrief, analysisId: string): string {
  const lines: string[] = [
    `# ASIS Strategic Brief`,
    `*Analysis ID: ${analysisId}*`,
    ``,
    `## Lead Recommendation`,
    brief.recommendation,
    ``,
    `**Confidence:** ${brief.confidence_score.toFixed(1)}/10 | **Data Quality:** ${brief.data_quality_score.toFixed(1)}/10`,
    ``,
    `## Executive Summary`,
    brief.executive_summary,
    ``,
    `## Strategic Options`,
    ...brief.strategic_options.map(
      (o) =>
        `### ${o.option_id}: ${o.title}${o.recommended ? " ✓ (Recommended)" : ""}\n${o.description}\n\n**Risk:** ${o.risk_level}\n\n**Pros:** ${o.pros.join(", ")}\n\n**Cons:** ${o.cons.join(", ")}`
    ),
    ``,
    `## Risk Assessment`,
    brief.risk_summary,
    ``,
    `## Financial Considerations`,
    brief.financial_summary,
    ``,
    `## Next Steps`,
    ...brief.next_steps.map(
      (s) => `${s.priority}. **${s.action}** (${s.owner}) — ${s.timeline}`
    ),
    ``,
    `## Sources`,
    ...brief.sources.map((s, i) => `[${i + 1}] ${s}`),
  ];

  if (brief.caveats.length) {
    lines.push(``, `## Caveats`, ...brief.caveats.map((c) => `- ${c}`));
  }

  return lines.join("\n");
}
