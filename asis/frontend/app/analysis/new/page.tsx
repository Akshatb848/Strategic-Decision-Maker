"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { streamAnalysis } from "@/lib/stream";
import { ArrowLeft, Cpu, Send } from "lucide-react";
import Link from "next/link";

interface FormState {
  query: string;
  company_name: string;
  sector: string;
  target_market: string;
  hq_country: string;
  annual_revenue_usd_mn: string;
  employee_count: string;
  additional_context: string;
  run_baseline: boolean;
}

const INITIAL: FormState = {
  query: "",
  company_name: "",
  sector: "",
  target_market: "",
  hq_country: "",
  annual_revenue_usd_mn: "",
  employee_count: "",
  additional_context: "",
  run_baseline: false,
};

const SECTORS = [
  "Technology", "Financial Services", "Healthcare", "Consumer Goods",
  "Energy", "Industrials", "Real Estate", "Telecommunications",
  "Media & Entertainment", "Retail", "Automotive", "Pharmaceuticals", "Other",
];

export default function NewAnalysisPage() {
  const router = useRouter();
  const [form, setForm] = useState<FormState>(INITIAL);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (form.query.length < 20) {
      setError("Query must be at least 20 characters.");
      return;
    }

    const token = localStorage.getItem("asis_token") ?? "";
    if (!token) {
      setError("Please log in first.");
      return;
    }

    setLoading(true);

    const request = {
      query: form.query,
      company_context: {
        company_name: form.company_name,
        sector: form.sector,
        target_market: form.target_market,
        hq_country: form.hq_country,
        annual_revenue_usd_mn: form.annual_revenue_usd_mn
          ? parseFloat(form.annual_revenue_usd_mn)
          : undefined,
        employee_count: form.employee_count
          ? parseInt(form.employee_count, 10)
          : undefined,
        additional_context: form.additional_context || undefined,
      },
      options: { run_baseline: form.run_baseline },
    };

    let analysisId: string | null = null;

    streamAnalysis(
      request,
      token,
      (event) => {
        if (event.type === "analysis_complete") {
          analysisId = event.data.analysis_id;
        }
      },
      () => {
        setLoading(false);
        if (analysisId) router.push(`/analysis/${analysisId}`);
      },
      (err) => {
        setLoading(false);
        setError(err.message);
      }
    );
  };

  const set = (field: keyof FormState) => (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
  ) => setForm((f) => ({ ...f, [field]: e.target.value }));

  return (
    <div className="min-h-screen bg-surface">
      {/* Header */}
      <header className="border-b border-surface-border px-8 py-4 flex items-center gap-4">
        <Link href="/" className="text-gray-400 hover:text-white transition-colors">
          <ArrowLeft size={20} />
        </Link>
        <div className="flex items-center gap-3">
          <div className="w-7 h-7 bg-brand-500 rounded-md flex items-center justify-center">
            <Cpu size={15} className="text-white" />
          </div>
          <span className="text-white font-semibold text-sm">New Strategic Analysis</span>
        </div>
      </header>

      <main className="max-w-2xl mx-auto px-8 py-10">
        <h2 className="text-2xl font-bold text-white mb-1">Initiate Analysis</h2>
        <p className="text-gray-400 text-sm mb-8">
          Define your strategic question and company context. ASIS will orchestrate
          six specialist AI agents to produce a board-ready brief.
        </p>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Strategic Query */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Strategic Question <span className="text-red-400">*</span>
            </label>
            <textarea
              value={form.query}
              onChange={set("query")}
              required
              rows={3}
              placeholder="e.g. Should Acme Corp enter the Indian fintech market in 2026?"
              className="w-full bg-surface-card border border-surface-border rounded-lg px-4 py-3
                         text-white placeholder-gray-600 focus:outline-none focus:ring-2
                         focus:ring-brand-500 resize-none text-sm"
            />
          </div>

          {/* Company Context */}
          <div className="card space-y-4">
            <h3 className="text-white font-medium text-sm">Company Context</h3>

            <div className="grid grid-cols-2 gap-4">
              <Field label="Company Name *" value={form.company_name} onChange={set("company_name")} required />
              <div>
                <label className="block text-xs font-medium text-gray-400 mb-1.5">
                  Sector <span className="text-red-400">*</span>
                </label>
                <select
                  value={form.sector}
                  onChange={set("sector")}
                  required
                  className="w-full bg-surface border border-surface-border rounded-lg px-3 py-2
                             text-white text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                >
                  <option value="">Select sector…</option>
                  {SECTORS.map((s) => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <Field
                label="Target Market *"
                value={form.target_market}
                onChange={set("target_market")}
                required
                placeholder="e.g. India, Southeast Asia"
              />
              <Field
                label="HQ Country"
                value={form.hq_country}
                onChange={set("hq_country")}
                placeholder="e.g. United Kingdom"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <Field
                label="Annual Revenue (USD mn)"
                value={form.annual_revenue_usd_mn}
                onChange={set("annual_revenue_usd_mn")}
                type="number"
                placeholder="e.g. 500"
              />
              <Field
                label="Employee Count"
                value={form.employee_count}
                onChange={set("employee_count")}
                type="number"
                placeholder="e.g. 2500"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-400 mb-1.5">
                Additional Context (optional)
              </label>
              <textarea
                value={form.additional_context}
                onChange={set("additional_context")}
                rows={2}
                placeholder="Any strategic context, constraints, or focus areas…"
                className="w-full bg-surface border border-surface-border rounded-lg px-3 py-2
                           text-white placeholder-gray-600 text-sm focus:outline-none
                           focus:ring-2 focus:ring-brand-500 resize-none"
              />
            </div>
          </div>

          {/* Options */}
          <div className="flex items-center gap-3">
            <input
              id="baseline"
              type="checkbox"
              checked={form.run_baseline}
              onChange={(e) =>
                setForm((f) => ({ ...f, run_baseline: e.target.checked }))
              }
              className="w-4 h-4 rounded border-surface-border bg-surface-card text-brand-500
                         focus:ring-brand-500"
            />
            <label htmlFor="baseline" className="text-sm text-gray-400">
              Also run single-agent baseline (for dissertation comparison)
            </label>
          </div>

          {error && (
            <div className="bg-red-900/30 border border-red-800/50 rounded-lg px-4 py-3 text-red-300 text-sm">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="btn-primary w-full flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Initiating pipeline…
              </>
            ) : (
              <>
                <Send size={16} />
                Launch ASIS Analysis
              </>
            )}
          </button>
        </form>
      </main>
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
  required,
  placeholder,
  type = "text",
}: {
  label: string;
  value: string;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  required?: boolean;
  placeholder?: string;
  type?: string;
}) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-400 mb-1.5">{label}</label>
      <input
        type={type}
        value={value}
        onChange={onChange}
        required={required}
        placeholder={placeholder}
        className="w-full bg-surface border border-surface-border rounded-lg px-3 py-2
                   text-white placeholder-gray-600 text-sm focus:outline-none
                   focus:ring-2 focus:ring-brand-500"
      />
    </div>
  );
}
