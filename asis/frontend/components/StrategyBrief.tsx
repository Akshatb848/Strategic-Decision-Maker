"use client";

import type { StrategicBrief } from "@/lib/api";
import { ExportControls } from "./ExportControls";
import { RiskMatrix } from "./RiskMatrix";
import { CheckCircle2, AlertTriangle, TrendingUp, Target, ChevronDown, ChevronUp } from "lucide-react";
import { useState } from "react";

interface Props {
  brief: StrategicBrief;
  analysisId: string;
}

export function StrategyBrief({ brief, analysisId }: Props) {
  const [showSources, setShowSources] = useState(false);

  return (
    <div className="space-y-4">
      {/* Export Controls */}
      <div className="flex justify-end">
        <ExportControls brief={brief} analysisId={analysisId} />
      </div>

      {/* Recommendation Banner */}
      <div className="bg-brand-900/30 border border-brand-700/50 rounded-xl p-5">
        <div className="flex items-start gap-3">
          <Target size={18} className="text-brand-400 shrink-0 mt-0.5" />
          <div>
            <p className="text-brand-300 text-xs font-semibold uppercase tracking-wider mb-1">
              Lead Recommendation
            </p>
            <p className="text-white font-medium leading-relaxed">{brief.recommendation}</p>
          </div>
        </div>
      </div>

      {/* Scores */}
      <div className="grid grid-cols-2 gap-3">
        <ScoreCard label="Confidence" score={brief.confidence_score} />
        <ScoreCard label="Data Quality" score={brief.data_quality_score} />
      </div>

      {/* Executive Summary */}
      <Section title="Executive Summary" icon={<TrendingUp size={15} />}>
        <p className="text-gray-300 text-sm leading-relaxed whitespace-pre-wrap">
          {brief.executive_summary}
        </p>
      </Section>

      {/* Strategic Options */}
      <Section title="Strategic Options" icon={<Target size={15} />}>
        <div className="space-y-3">
          {brief.strategic_options.map((opt) => (
            <div
              key={opt.option_id}
              className={`rounded-lg p-4 border ${
                opt.recommended
                  ? "border-brand-700/50 bg-brand-900/20"
                  : "border-surface-border bg-surface"
              }`}
            >
              <div className="flex items-start justify-between gap-2 mb-2">
                <p className="text-white font-medium text-sm">{opt.title}</p>
                <div className="flex items-center gap-2 shrink-0">
                  {opt.recommended && (
                    <span className="badge badge-blue text-xs">Recommended</span>
                  )}
                  <RiskBadge level={opt.risk_level} />
                </div>
              </div>
              <p className="text-gray-400 text-xs mb-3">{opt.description}</p>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <p className="text-emerald-400 text-xs font-medium mb-1">Pros</p>
                  <ul className="space-y-0.5">
                    {opt.pros.map((p, i) => (
                      <li key={i} className="text-gray-300 text-xs flex items-start gap-1.5">
                        <CheckCircle2 size={10} className="text-emerald-500 shrink-0 mt-0.5" />
                        {p}
                      </li>
                    ))}
                  </ul>
                </div>
                <div>
                  <p className="text-amber-400 text-xs font-medium mb-1">Cons</p>
                  <ul className="space-y-0.5">
                    {opt.cons.map((c, i) => (
                      <li key={i} className="text-gray-300 text-xs flex items-start gap-1.5">
                        <AlertTriangle size={10} className="text-amber-500 shrink-0 mt-0.5" />
                        {c}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
              {opt.estimated_investment_usd_mn != null && (
                <p className="text-gray-500 text-xs mt-2">
                  Est. investment: ${opt.estimated_investment_usd_mn}M
                  {opt.time_to_value ? ` · ${opt.time_to_value}` : ""}
                </p>
              )}
            </div>
          ))}
        </div>
      </Section>

      {/* Risk Summary */}
      <Section title="Risk Assessment" icon={<AlertTriangle size={15} />}>
        <p className="text-gray-300 text-sm leading-relaxed mb-3">{brief.risk_summary}</p>
        <RiskMatrix />
      </Section>

      {/* Financial Summary */}
      <Section title="Financial Considerations" icon={<TrendingUp size={15} />}>
        <p className="text-gray-300 text-sm leading-relaxed">{brief.financial_summary}</p>
      </Section>

      {/* Next Steps */}
      <Section title="Next Steps" icon={<CheckCircle2 size={15} />}>
        <div className="space-y-2">
          {brief.next_steps
            .sort((a, b) => a.priority - b.priority)
            .map((step, i) => (
              <div key={i} className="flex gap-3 p-3 bg-surface rounded-lg border border-surface-border">
                <div className="w-6 h-6 bg-brand-500/20 text-brand-400 rounded-full flex items-center justify-center shrink-0 text-xs font-bold">
                  {step.priority}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-white text-sm font-medium">{step.action}</p>
                  <p className="text-gray-500 text-xs mt-0.5">
                    {step.owner} · {step.timeline}
                  </p>
                  <p className="text-gray-600 text-xs mt-0.5 italic">{step.success_criteria}</p>
                </div>
              </div>
            ))}
        </div>
      </Section>

      {/* Sources */}
      {brief.sources.length > 0 && (
        <div className="card">
          <button
            onClick={() => setShowSources((s) => !s)}
            className="flex items-center justify-between w-full text-left"
          >
            <span className="text-gray-400 text-xs font-medium">
              Sources ({brief.sources.length})
            </span>
            {showSources ? (
              <ChevronUp size={14} className="text-gray-500" />
            ) : (
              <ChevronDown size={14} className="text-gray-500" />
            )}
          </button>
          {showSources && (
            <ul className="mt-3 space-y-1">
              {brief.sources.map((src, i) => (
                <li key={i} className="text-gray-500 text-xs">
                  [{i + 1}] {src}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* Caveats */}
      {brief.caveats.length > 0 && (
        <div className="card border-amber-900/30 bg-amber-900/5">
          <p className="text-amber-400 text-xs font-medium mb-2">Caveats</p>
          <ul className="space-y-1">
            {brief.caveats.map((c, i) => (
              <li key={i} className="text-gray-400 text-xs">{c}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

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
    <div className="card">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-brand-400">{icon}</span>
        <h4 className="text-white font-medium text-sm">{title}</h4>
      </div>
      {children}
    </div>
  );
}

function ScoreCard({ label, score }: { label: string; score: number }) {
  const color =
    score >= 7.5 ? "text-emerald-400" : score >= 5 ? "text-amber-400" : "text-red-400";
  const bg =
    score >= 7.5 ? "bg-emerald-900/20 border-emerald-800/30"
    : score >= 5 ? "bg-amber-900/20 border-amber-800/30"
    : "bg-red-900/20 border-red-800/30";
  return (
    <div className={`rounded-lg border p-3 ${bg}`}>
      <p className="text-gray-400 text-xs mb-1">{label}</p>
      <p className={`text-xl font-bold ${color}`}>
        {score.toFixed(1)}<span className="text-gray-600 text-sm font-normal">/10</span>
      </p>
    </div>
  );
}

function RiskBadge({ level }: { level: string }) {
  const cls =
    level === "low" ? "badge-green" : level === "medium" ? "badge-yellow" : "badge-red";
  return <span className={`badge ${cls} text-xs capitalize`}>{level}</span>;
}
