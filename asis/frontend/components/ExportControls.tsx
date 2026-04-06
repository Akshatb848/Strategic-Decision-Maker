"use client";

import type { StrategicBrief } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { FileText, Download } from "lucide-react";

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
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <Button
        variant="ghost"
        size="sm"
        leftIcon={<FileText size={13} />}
        onClick={exportMarkdown}
      >
        Export MD
      </Button>
      <Button
        variant="ghost"
        size="sm"
        leftIcon={<Download size={13} />}
        onClick={exportJSON}
      >
        Export JSON
      </Button>
    </div>
  );
}

function briefToMarkdown(brief: StrategicBrief, analysisId: string): string {
  const lines: string[] = [
    `# ASIS Strategic Brief`,
    `*Analysis ID: ${analysisId}*`,
    ``,
    `## Board Decision: ${brief.decision_recommendation}`,
    `*${brief.board_narrative}*`,
    ``,
    `**Overall Confidence:** ${brief.overall_confidence}/100`,
    ``,
    `## Executive Summary`,
    brief.executive_summary,
    ``,
    `## Strategic Imperatives`,
    ...(brief.strategic_imperatives ?? []).map((imp, i) => `${i + 1}. ${imp}`),
    ``,
    `## Strategic Roadmap`,
    ...(brief.roadmap ?? []).flatMap((phase) => [
      `### ${phase.phase} — ${phase.investment}`,
      `*${phase.focus}*`,
      ``,
      ...(phase.key_actions ?? []).map((a) => `- ${a}`),
      ``,
      `**KPI:** ${phase.success_metric}`,
      ``,
    ]),
    `## Balanced Scorecard`,
    ...(brief.balanced_scorecard
      ? [
          `- **Financial:** ${brief.balanced_scorecard.financial}`,
          `- **Customer:** ${brief.balanced_scorecard.customer}`,
          `- **Internal Process:** ${brief.balanced_scorecard.internal_process}`,
          `- **Learning & Growth:** ${brief.balanced_scorecard.learning_growth}`,
        ]
      : []),
    ``,
    `## Success Metrics`,
    ...(brief.success_metrics ?? []).map((m) => `- ${m}`),
  ];

  if (brief.dissertation_contribution) {
    lines.push(``, `---`, `*${brief.dissertation_contribution}*`);
  }

  return lines.join("\n");
}
