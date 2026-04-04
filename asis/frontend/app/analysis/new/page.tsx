"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { scaleIn } from "@/lib/animations";
import { streamAnalysis } from "@/lib/stream";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Send, ArrowRight, ArrowLeft, Building2, FileSearch, Settings2 } from "lucide-react";

interface FormState {
  // Step 1 — Company
  company_name: string;
  sector: string;
  geography: string;
  hq_country: string;
  annual_revenue_usd_mn: string;
  employee_count: string;
  // Step 2 — Query
  query: string;
  analysis_type: "full" | "market" | "risk" | "financial";
  additional_context: string;
  // Step 3 — Options
  confidence_threshold: number;
  use_rag: boolean;
  use_memory: boolean;
  run_baseline: boolean;
}

const INITIAL: FormState = {
  company_name: "",
  sector: "",
  geography: "",
  hq_country: "",
  annual_revenue_usd_mn: "",
  employee_count: "",
  query: "",
  analysis_type: "full",
  additional_context: "",
  confidence_threshold: 7,
  use_rag: true,
  use_memory: false,
  run_baseline: false,
};

const SECTORS = [
  "Technology", "Financial Services", "Healthcare", "Consumer Goods",
  "Energy", "Industrials", "Real Estate", "Telecommunications",
  "Media & Entertainment", "Retail", "Automotive", "Pharmaceuticals", "Other",
];

const ANALYSIS_TYPES: Array<{ value: FormState["analysis_type"]; label: string; desc: string }> = [
  { value: "full", label: "Full Analysis", desc: "All 6 agents — market, risk, financial, competitor" },
  { value: "market", label: "Market Focus", desc: "Deep market intelligence & competitive positioning" },
  { value: "risk", label: "Risk Focus", desc: "Comprehensive risk assessment & mitigation" },
  { value: "financial", label: "Financial Focus", desc: "Investment analysis & financial modelling" },
];

const STEPS = [
  { label: "Company", icon: Building2 },
  { label: "Query", icon: FileSearch },
  { label: "Options", icon: Settings2 },
];

export default function NewAnalysisPage() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [form, setForm] = useState<FormState>(INITIAL);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const set =
    <K extends keyof FormState>(field: K) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
      setForm((f) => ({ ...f, [field]: e.target.value }));

  const setDirect = <K extends keyof FormState>(field: K, value: FormState[K]) =>
    setForm((f) => ({ ...f, [field]: value }));

  const validateStep = (): string | null => {
    if (step === 0) {
      if (!form.company_name.trim()) return "Company name is required.";
      if (!form.sector) return "Please select a sector.";
      if (!form.geography.trim()) return "Geography / target market is required.";
    }
    if (step === 1) {
      if (form.query.trim().length < 20) return "Query must be at least 20 characters.";
    }
    return null;
  };

  const handleNext = () => {
    const err = validateStep();
    if (err) { setError(err); return; }
    setError(null);
    setStep((s) => s + 1);
  };

  const handleBack = () => {
    setError(null);
    setStep((s) => Math.max(0, s - 1));
  };

  const handleSubmit = () => {
    setError(null);
    const token = localStorage.getItem("asis_token") ?? "";
    if (!token) { setError("Please log in first."); return; }

    setLoading(true);

    const request = {
      query: form.query,
      company_context: {
        company_name: form.company_name,
        sector: form.sector,
        target_market: form.geography,
        hq_country: form.hq_country || undefined,
        annual_revenue_usd_mn: form.annual_revenue_usd_mn
          ? parseFloat(form.annual_revenue_usd_mn)
          : undefined,
        employee_count: form.employee_count
          ? parseInt(form.employee_count, 10)
          : undefined,
        additional_context: form.additional_context || undefined,
      },
      options: {
        run_baseline: form.run_baseline,
        analysis_type: form.analysis_type,
        confidence_threshold: form.confidence_threshold,
        use_rag: form.use_rag,
        use_memory: form.use_memory,
      },
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

  return (
    <div style={{ maxWidth: 640, margin: "0 auto", padding: "32px 24px 64px" }}>
      {/* Page title */}
      <div style={{ marginBottom: 28 }}>
        <h1
          style={{
            fontSize: 20,
            fontWeight: 700,
            color: "var(--text-primary)",
            letterSpacing: "-0.02em",
            marginBottom: 4,
          }}
        >
          New Strategic Analysis
        </h1>
        <p style={{ fontSize: 13, color: "var(--text-secondary)" }}>
          Define your strategic question. ASIS orchestrates six specialist AI agents
          to produce a board-ready brief.
        </p>
      </div>

      {/* Step indicator */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 0,
          marginBottom: 28,
          backgroundColor: "var(--bg-surface)",
          border: "1px solid var(--border)",
          borderRadius: "var(--radius-lg)",
          padding: "4px",
        }}
      >
        {STEPS.map((s, i) => {
          const isActive = i === step;
          const isDone = i < step;
          const Icon = s.icon;
          return (
            <div
              key={s.label}
              style={{
                flex: 1,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: 6,
                padding: "8px 12px",
                borderRadius: "var(--radius-md)",
                backgroundColor: isActive
                  ? "var(--bg-elevated)"
                  : "transparent",
                fontSize: 12,
                fontWeight: isActive ? 600 : 400,
                color: isActive
                  ? "var(--text-primary)"
                  : isDone
                  ? "var(--accent)"
                  : "var(--text-tertiary)",
                transition: "all var(--transition-fast)",
              }}
            >
              <Icon size={13} />
              <span>
                {i + 1}. {s.label}
              </span>
              {isDone && (
                <span style={{ color: "var(--success)", fontSize: 10 }}>✓</span>
              )}
            </div>
          );
        })}
      </div>

      {/* Step panels */}
      <AnimatePresence mode="wait">
        <motion.div
          key={step}
          initial={scaleIn.initial}
          animate={scaleIn.animate}
          exit={{ opacity: 0, scale: 0.97 }}
          transition={scaleIn.transition}
        >
          {step === 0 && (
            <Step1 form={form} set={set} />
          )}
          {step === 1 && (
            <Step2
              form={form}
              set={set}
              setDirect={setDirect}
            />
          )}
          {step === 2 && (
            <Step3
              form={form}
              set={set}
              setDirect={setDirect}
            />
          )}
        </motion.div>
      </AnimatePresence>

      {/* Error */}
      {error && (
        <motion.div
          initial={{ opacity: 0, y: -4 }}
          animate={{ opacity: 1, y: 0 }}
          style={{
            marginTop: 16,
            padding: "12px 16px",
            backgroundColor: "var(--danger-dim)",
            border: "1px solid rgba(239,68,68,0.3)",
            borderRadius: "var(--radius-md)",
            fontSize: 13,
            color: "var(--danger)",
          }}
        >
          {error}
        </motion.div>
      )}

      {/* Navigation */}
      <div
        style={{
          marginTop: 24,
          display: "flex",
          justifyContent: "space-between",
          gap: 12,
        }}
      >
        {step > 0 ? (
          <Button
            variant="outline"
            size="md"
            leftIcon={<ArrowLeft size={14} />}
            onClick={handleBack}
            disabled={loading}
          >
            Back
          </Button>
        ) : (
          <div />
        )}

        {step < 2 ? (
          <Button
            variant="primary"
            size="md"
            rightIcon={<ArrowRight size={14} />}
            onClick={handleNext}
          >
            Continue
          </Button>
        ) : (
          <Button
            variant="primary"
            size="md"
            loading={loading}
            leftIcon={loading ? undefined : <Send size={14} />}
            onClick={handleSubmit}
          >
            {loading ? "Launching pipeline…" : "Launch ASIS Analysis"}
          </Button>
        )}
      </div>
    </div>
  );
}

/* ─── Step sub-components ─────────────────────────────────────────────────── */

function Step1({
  form,
  set,
}: {
  form: FormState;
  set: <K extends keyof FormState>(
    field: K
  ) => (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
  ) => void;
}) {
  return (
    <Card padding="lg">
      <h2
        style={{
          fontSize: 14,
          fontWeight: 600,
          color: "var(--text-primary)",
          marginBottom: 20,
        }}
      >
        Company Context
      </h2>
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <FieldRow>
          <FormField
            label="Company Name *"
            value={form.company_name}
            onChange={set("company_name")}
            required
            placeholder="e.g. Acme Corp"
          />
          <div>
            <label style={labelStyle}>Sector *</label>
            <select
              value={form.sector}
              onChange={set("sector")}
              required
              style={inputStyle}
            >
              <option value="">Select sector…</option>
              {SECTORS.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>
        </FieldRow>

        <FieldRow>
          <FormField
            label="Target Geography / Market *"
            value={form.geography}
            onChange={set("geography")}
            required
            placeholder="e.g. India, Southeast Asia"
          />
          <FormField
            label="HQ Country"
            value={form.hq_country}
            onChange={set("hq_country")}
            placeholder="e.g. United Kingdom"
          />
        </FieldRow>

        <FieldRow>
          <FormField
            label="Annual Revenue (USD mn)"
            value={form.annual_revenue_usd_mn}
            onChange={set("annual_revenue_usd_mn")}
            type="number"
            placeholder="e.g. 500"
          />
          <FormField
            label="Employee Count"
            value={form.employee_count}
            onChange={set("employee_count")}
            type="number"
            placeholder="e.g. 2500"
          />
        </FieldRow>
      </div>
    </Card>
  );
}

function Step2({
  form,
  set,
  setDirect,
}: {
  form: FormState;
  set: <K extends keyof FormState>(
    field: K
  ) => (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
  ) => void;
  setDirect: <K extends keyof FormState>(field: K, value: FormState[K]) => void;
}) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <Card padding="lg">
        <h2
          style={{
            fontSize: 14,
            fontWeight: 600,
            color: "var(--text-primary)",
            marginBottom: 16,
          }}
        >
          Strategic Question *
        </h2>
        <textarea
          value={form.query}
          onChange={set("query")}
          required
          rows={4}
          placeholder="e.g. Should Acme Corp enter the Indian fintech market in 2026, and if so, which entry mode offers the highest risk-adjusted return?"
          style={{
            ...inputStyle,
            width: "100%",
            resize: "vertical",
            fontFamily: "var(--font-mono)",
            fontSize: 13,
            lineHeight: 1.6,
          }}
        />
        <p
          style={{
            marginTop: 6,
            fontSize: 11,
            color:
              form.query.length >= 20
                ? "var(--success)"
                : "var(--text-tertiary)",
          }}
        >
          {form.query.length} chars — minimum 20 required
        </p>
      </Card>

      <Card padding="lg">
        <h2
          style={{
            fontSize: 14,
            fontWeight: 600,
            color: "var(--text-primary)",
            marginBottom: 16,
          }}
        >
          Analysis Type
        </h2>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: 8,
          }}
        >
          {ANALYSIS_TYPES.map((t) => {
            const isSelected = form.analysis_type === t.value;
            return (
              <button
                key={t.value}
                type="button"
                onClick={() => setDirect("analysis_type", t.value)}
                style={{
                  padding: "10px 12px",
                  borderRadius: "var(--radius-md)",
                  border: isSelected
                    ? "1px solid var(--accent)"
                    : "1px solid var(--border)",
                  backgroundColor: isSelected
                    ? "var(--accent-dim)"
                    : "var(--bg-elevated)",
                  color: isSelected ? "var(--accent)" : "var(--text-secondary)",
                  textAlign: "left",
                  cursor: "pointer",
                  transition: "all var(--transition-fast)",
                }}
              >
                <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 3 }}>
                  {t.label}
                </div>
                <div
                  style={{
                    fontSize: 11,
                    color: isSelected
                      ? "var(--accent)"
                      : "var(--text-tertiary)",
                    lineHeight: 1.4,
                    opacity: 0.85,
                  }}
                >
                  {t.desc}
                </div>
              </button>
            );
          })}
        </div>
      </Card>

      <Card padding="lg">
        <label style={labelStyle}>Additional Context (optional)</label>
        <textarea
          value={form.additional_context}
          onChange={set("additional_context")}
          rows={2}
          placeholder="Strategic constraints, focus areas, or key assumptions…"
          style={{
            ...inputStyle,
            width: "100%",
            resize: "vertical",
            marginTop: 6,
          }}
        />
      </Card>
    </div>
  );
}

function Step3({
  form,
  setDirect,
}: {
  form: FormState;
  set: <K extends keyof FormState>(
    field: K
  ) => (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
  ) => void;
  setDirect: <K extends keyof FormState>(field: K, value: FormState[K]) => void;
}) {
  return (
    <Card padding="lg">
      <h2
        style={{
          fontSize: 14,
          fontWeight: 600,
          color: "var(--text-primary)",
          marginBottom: 20,
        }}
      >
        Analysis Options
      </h2>

      <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
        {/* Confidence slider */}
        <div>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: 10,
            }}
          >
            <label style={{ ...labelStyle, margin: 0 }}>
              Confidence Threshold
            </label>
            <span
              style={{
                fontSize: 13,
                fontWeight: 700,
                color: "var(--accent)",
              }}
            >
              {form.confidence_threshold}/10
            </span>
          </div>
          <input
            type="range"
            min={1}
            max={10}
            step={0.5}
            value={form.confidence_threshold}
            onChange={(e) =>
              setDirect("confidence_threshold", parseFloat(e.target.value))
            }
            style={{
              width: "100%",
              accentColor: "var(--accent)",
              cursor: "pointer",
              background: "transparent",
              border: "none",
            }}
          />
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              fontSize: 10,
              color: "var(--text-tertiary)",
              marginTop: 4,
            }}
          >
            <span>1 — Permissive</span>
            <span>10 — Strict</span>
          </div>
        </div>

        {/* Toggles */}
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <ToggleRow
            label="RAG Knowledge Retrieval"
            description="Search external knowledge bases to enrich analysis"
            checked={form.use_rag}
            onChange={(v) => setDirect("use_rag", v)}
          />
          <ToggleRow
            label="Memory Context"
            description="Include previous analyses for this company"
            checked={form.use_memory}
            onChange={(v) => setDirect("use_memory", v)}
          />
          <ToggleRow
            label="Single-Agent Baseline"
            description="Run baseline comparison (adds ~30s)"
            checked={form.run_baseline}
            onChange={(v) => setDirect("run_baseline", v)}
          />
        </div>

        {/* Summary */}
        <div
          style={{
            padding: "12px 14px",
            backgroundColor: "var(--bg-elevated)",
            borderRadius: "var(--radius-md)",
            border: "1px solid var(--border)",
          }}
        >
          <p
            style={{
              fontSize: 11,
              color: "var(--text-tertiary)",
              marginBottom: 6,
              textTransform: "uppercase",
              letterSpacing: "0.04em",
            }}
          >
            Review
          </p>
          <p style={{ fontSize: 12, color: "var(--text-secondary)" }}>
            <strong style={{ color: "var(--text-primary)" }}>
              {form.company_name}
            </strong>{" "}
            · {form.sector} · {form.geography}
          </p>
          <p
            style={{
              fontSize: 12,
              color: "var(--text-tertiary)",
              marginTop: 4,
              fontFamily: "var(--font-mono)",
            }}
          >
            {form.query.length > 80
              ? `${form.query.slice(0, 80)}…`
              : form.query}
          </p>
        </div>
      </div>
    </Card>
  );
}

/* ─── Shared helpers ──────────────────────────────────────────────────────── */

function FieldRow({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
      {children}
    </div>
  );
}

function FormField({
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
      <label style={labelStyle}>{label}</label>
      <input
        type={type}
        value={value}
        onChange={onChange}
        required={required}
        placeholder={placeholder}
        style={{ ...inputStyle, width: "100%", marginTop: 6 }}
      />
    </div>
  );
}

function ToggleRow({
  label,
  description,
  checked,
  onChange,
}: {
  label: string;
  description: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <label
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: 12,
        padding: "10px 12px",
        borderRadius: "var(--radius-md)",
        border: "1px solid var(--border)",
        cursor: "pointer",
        backgroundColor: checked ? "var(--accent-dim)" : "var(--bg-elevated)",
        transition: "all var(--transition-fast)",
      }}
    >
      <div>
        <div
          style={{
            fontSize: 12,
            fontWeight: 500,
            color: checked ? "var(--accent)" : "var(--text-primary)",
          }}
        >
          {label}
        </div>
        <div
          style={{
            fontSize: 11,
            color: "var(--text-tertiary)",
            marginTop: 2,
          }}
        >
          {description}
        </div>
      </div>
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        style={{ accentColor: "var(--accent)", width: 16, height: 16, cursor: "pointer" }}
      />
    </label>
  );
}

const labelStyle: React.CSSProperties = {
  display: "block",
  fontSize: 11,
  fontWeight: 500,
  color: "var(--text-secondary)",
  textTransform: "uppercase",
  letterSpacing: "0.04em",
};

const inputStyle: React.CSSProperties = {
  padding: "8px 12px",
  borderRadius: "var(--radius-md)",
  border: "1px solid var(--border)",
  backgroundColor: "var(--bg-elevated)",
  color: "var(--text-primary)",
  fontSize: 13,
  outline: "none",
  fontFamily: "var(--font-sans)",
  width: "100%",
};
