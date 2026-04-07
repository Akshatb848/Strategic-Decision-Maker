"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { listReports, type AnalysisSummary } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import { formatDistanceToNow } from "date-fns";
import { staggerContainer, staggerItem, fadeUp } from "@/lib/animations";
import { Card } from "@/components/ui/Card";
import { StatusBadge } from "@/components/ui/Badge";
import { StatusDot } from "@/components/ui/StatusDot";
import {
  BarChart3, Plus, FileText, TrendingUp, Shield, Clock,
  AlertCircle, ChevronRight, Zap, ArrowRight, CheckCircle, XCircle, MinusCircle,
} from "lucide-react";

// ── Welcome page (unauthenticated) ───────────────────────────────────────────

const AGENTS = [
  { icon: "◈", name: "Orchestrator", framework: "Minto Pyramid + Issue Trees", desc: "Decomposes problems with MECE logic", color: "#7c3aed" },
  { icon: "◎", name: "Market Intelligence", framework: "PESTLE + Porter's Five Forces", desc: "Maps the regulatory and competitive landscape", color: "#0ea5e9" },
  { icon: "◇", name: "Risk Assessment", framework: "COSO ERM 2017 + ISO 31000", desc: "Quantifies multi-domain enterprise risk", color: "#ef4444" },
  { icon: "◉", name: "Competitor Analysis", framework: "Porter's Generic Strategies", desc: "Benchmarks position vs. named competitors", color: "#f59e0b" },
  { icon: "◆", name: "Financial Reasoning", framework: "McKinsey 3 Horizons + NPV/IRR", desc: "Models ROI scenarios with payback analysis", color: "#10b981" },
  { icon: "◍", name: "Synthesis", framework: "Balanced Scorecard + McKinsey 7-S", desc: "Delivers board-ready strategic recommendations", color: "#8b5cf6" },
];

const COMPARISON = [
  { label: "Generic LLM", icon: XCircle, color: "var(--danger)", items: ["Unstructured free-text responses", "No strategic framework grounding", "Cannot quantify risk or model ROI", "No board-ready output format", "Single model, no specialisation"] },
  { label: "ASIS", icon: CheckCircle, color: "var(--success)", items: ["Structured JSON → visual decision output", "6 frameworks applied simultaneously", "COSO ERM risk register + financial scenarios", "Board-ready narrative + 3-phase roadmap", "6 specialist agents, <60 seconds"] },
  { label: "Traditional Consulting", icon: MinusCircle, color: "var(--warning)", items: ["6-week engagement timeline", "$250k+ minimum engagement", "Human availability constraints", "Point-in-time analysis only", "Single firm's methodology"] },
];

function WelcomePage() {
  const router = useRouter();
  const [question, setQuestion] = useState("");

  const typewriterPhrases = ["McKinsey Partner", "Board Advisor", "Strategy Director", "Chief Risk Officer"];
  const [phraseIdx, setPhraseIdx] = useState(0);
  const [displayed, setDisplayed] = useState("");
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    const target = typewriterPhrases[phraseIdx];
    if (!deleting && displayed.length < target.length) {
      const t = setTimeout(() => setDisplayed(target.slice(0, displayed.length + 1)), 80);
      return () => clearTimeout(t);
    }
    if (!deleting && displayed.length === target.length) {
      const t = setTimeout(() => setDeleting(true), 1800);
      return () => clearTimeout(t);
    }
    if (deleting && displayed.length > 0) {
      const t = setTimeout(() => setDisplayed(displayed.slice(0, -1)), 40);
      return () => clearTimeout(t);
    }
    if (deleting && displayed.length === 0) {
      setDeleting(false);
      setPhraseIdx((i) => (i + 1) % typewriterPhrases.length);
    }
  }, [displayed, deleting, phraseIdx]);

  function handleAnalyse(e: React.FormEvent) {
    e.preventDefault();
    if (question.trim()) {
      router.push(`/register?q=${encodeURIComponent(question.trim())}`);
    } else {
      router.push("/register");
    }
  }

  return (
    <div style={{ background: "#070b14", minHeight: "100vh", color: "#f1f5f9" }}>
      {/* ── HERO ──────────────────────────────────────────────────────────── */}
      <div
        style={{
          minHeight: "100vh",
          display: "flex",
          flexDirection: "column",
          position: "relative",
          overflow: "hidden",
        }}
      >
        {/* Background orbs */}
        {[
          { top: "10%", left: "15%", color: "rgba(99,102,241,0.12)", size: 500 },
          { top: "40%", right: "10%", color: "rgba(124,58,237,0.08)", size: 600 },
          { bottom: "10%", left: "40%", color: "rgba(20,184,166,0.06)", size: 400 },
        ].map((orb, i) => (
          <div
            key={i}
            style={{
              position: "absolute",
              width: orb.size,
              height: orb.size,
              borderRadius: "50%",
              background: orb.color,
              filter: "blur(80px)",
              top: orb.top,
              left: (orb as any).left,
              right: (orb as any).right,
              bottom: orb.bottom,
              pointerEvents: "none",
            }}
          />
        ))}

        {/* Navbar */}
        <nav style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "20px 48px", position: "relative", zIndex: 10 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div style={{ width: 34, height: 34, borderRadius: 8, background: "linear-gradient(135deg, #6366f1, #7c3aed)", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <Zap size={16} color="white" />
            </div>
            <span style={{ fontSize: 15, fontWeight: 700, letterSpacing: "-0.01em" }}>ASIS</span>
            <span style={{ fontSize: 10, padding: "2px 6px", borderRadius: 4, background: "rgba(99,102,241,0.15)", color: "#818cf8", fontWeight: 600 }}>v3.0</span>
          </div>
          <div style={{ display: "flex", gap: 12 }}>
            <Link href="/login" style={{ padding: "8px 18px", borderRadius: 8, border: "1px solid rgba(255,255,255,0.12)", color: "#94a3b8", fontSize: 13, fontWeight: 500, textDecoration: "none" }}>
              Sign in
            </Link>
            <Link href="/register" style={{ padding: "8px 18px", borderRadius: 8, background: "linear-gradient(135deg, #6366f1, #7c3aed)", color: "white", fontSize: 13, fontWeight: 600, textDecoration: "none" }}>
              Get Started
            </Link>
          </div>
        </nav>

        {/* Hero content */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", textAlign: "center", padding: "60px 24px", position: "relative", zIndex: 10 }}>
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }}>
            <div style={{ fontSize: 11, letterSpacing: "0.1em", color: "#818cf8", fontWeight: 600, marginBottom: 24, textTransform: "uppercase" }}>
              Enterprise Strategic Intelligence
            </div>
          </motion.div>

          <motion.h1
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.1 }}
            style={{ fontSize: "clamp(36px, 6vw, 64px)", fontWeight: 800, letterSpacing: "-0.03em", lineHeight: 1.1, marginBottom: 16, maxWidth: 800 }}
          >
            The AI That Thinks Like a{" "}
            <span style={{ background: "linear-gradient(135deg, #6366f1, #a855f7)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
              {displayed}
              <span style={{ opacity: 1, animation: "blink 1s step-end infinite" }}>|</span>
            </span>
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.25 }}
            style={{ fontSize: 17, color: "#94a3b8", lineHeight: 1.7, maxWidth: 620, marginBottom: 40 }}
          >
            Six specialised AI agents that decompose complex enterprise problems, quantify multi-dimensional risk,
            benchmark competitive position, and deliver board-ready strategic decisions — in under 60 seconds.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.4 }}
            style={{ display: "flex", gap: 12, justifyContent: "center", flexWrap: "wrap" }}
          >
            <Link href="/register" style={{ display: "flex", alignItems: "center", gap: 8, padding: "12px 28px", borderRadius: 10, background: "linear-gradient(135deg, #6366f1, #7c3aed)", color: "white", fontSize: 15, fontWeight: 600, textDecoration: "none" }}>
              Start Free Analysis
              <ArrowRight size={16} />
            </Link>
            <Link href="/login" style={{ display: "flex", alignItems: "center", gap: 8, padding: "12px 28px", borderRadius: 10, border: "1px solid rgba(255,255,255,0.12)", color: "#cbd5e1", fontSize: 15, fontWeight: 500, textDecoration: "none" }}>
              Sign in
            </Link>
          </motion.div>

          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.6 }}
            style={{ fontSize: 11, color: "#475569", marginTop: 24 }}
          >
            Frameworks: McKinsey 7-S · COSO ERM 2017 · Porter's Five Forces · NIST CSF · Balanced Scorecard
          </motion.p>
        </div>
      </div>

      {/* ── AGENTS GRID ──────────────────────────────────────────────────── */}
      <div style={{ padding: "80px 48px", background: "#0c1220" }}>
        <div style={{ textAlign: "center", marginBottom: 48 }}>
          <h2 style={{ fontSize: 32, fontWeight: 800, letterSpacing: "-0.02em", marginBottom: 12 }}>
            6 Specialist Agents. One Unified Intelligence.
          </h2>
          <p style={{ fontSize: 15, color: "#94a3b8", maxWidth: 560, margin: "0 auto" }}>
            Each agent applies a distinct strategic framework. Together, they replicate what a full consulting team delivers in 6 weeks — in 60 seconds.
          </p>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 16, maxWidth: 1000, margin: "0 auto" }}>
          {AGENTS.map((agent, i) => (
            <motion.div
              key={agent.name}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.08 }}
              style={{
                padding: "20px 22px",
                borderRadius: 12,
                border: "1px solid rgba(255,255,255,0.06)",
                background: "#111827",
                borderLeft: `3px solid ${agent.color}`,
              }}
            >
              <div style={{ fontSize: 22, marginBottom: 8 }}>{agent.icon}</div>
              <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 4 }}>{agent.name}</div>
              <div style={{ fontSize: 11, color: agent.color, fontWeight: 600, marginBottom: 8 }}>{agent.framework}</div>
              <div style={{ fontSize: 12, color: "#94a3b8" }}>{agent.desc}</div>
            </motion.div>
          ))}
        </div>
      </div>

      {/* ── COMPARISON ───────────────────────────────────────────────────── */}
      <div style={{ padding: "80px 48px", background: "#070b14" }}>
        <div style={{ textAlign: "center", marginBottom: 48 }}>
          <h2 style={{ fontSize: 32, fontWeight: 800, letterSpacing: "-0.02em", marginBottom: 12 }}>
            Not a chatbot. A Strategic Intelligence System.
          </h2>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 20, maxWidth: 900, margin: "0 auto" }}>
          {COMPARISON.map(({ label, icon: Icon, color, items }) => (
            <div key={label} style={{ padding: "24px", borderRadius: 12, border: "1px solid rgba(255,255,255,0.06)", background: "#0c1220" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16 }}>
                <Icon size={18} style={{ color }} />
                <span style={{ fontSize: 14, fontWeight: 700 }}>{label}</span>
              </div>
              {items.map((item) => (
                <div key={item} style={{ display: "flex", alignItems: "flex-start", gap: 8, marginBottom: 10 }}>
                  <Icon size={12} style={{ color, flexShrink: 0, marginTop: 2 }} />
                  <span style={{ fontSize: 12, color: "#94a3b8" }}>{item}</span>
                </div>
              ))}
            </div>
          ))}
        </div>
      </div>

      {/* ── CTA ─────────────────────────────────────────────────────────── */}
      <div style={{ padding: "80px 48px", background: "#0c1220", textAlign: "center" }}>
        <h2 style={{ fontSize: 28, fontWeight: 800, letterSpacing: "-0.02em", marginBottom: 12 }}>
          Ready to run your first strategic analysis?
        </h2>
        <p style={{ fontSize: 14, color: "#94a3b8", marginBottom: 32 }}>Free to start · No credit card required · Results in 60 seconds</p>
        <form onSubmit={handleAnalyse} style={{ display: "flex", gap: 10, maxWidth: 580, margin: "0 auto", flexWrap: "wrap", justifyContent: "center" }}>
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Enter your strategic question…"
            style={{
              flex: 1,
              minWidth: 260,
              padding: "12px 16px",
              borderRadius: 10,
              border: "1px solid rgba(255,255,255,0.1)",
              background: "#111827",
              color: "#f1f5f9",
              fontSize: 14,
              outline: "none",
            }}
          />
          <button
            type="submit"
            style={{ padding: "12px 24px", borderRadius: 10, background: "linear-gradient(135deg, #6366f1, #7c3aed)", color: "white", fontSize: 14, fontWeight: 600, border: "none", cursor: "pointer" }}
          >
            Analyse →
          </button>
        </form>
        <p style={{ fontSize: 11, color: "#334155", marginTop: 40 }}>
          ASIS v3.0 · Built for enterprise strategic decision intelligence · MANG6550 Research · University of Southampton
        </p>
      </div>

      <style>{`@keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }`}</style>
    </div>
  );
}

// ── Dashboard page (authenticated) ──────────────────────────────────────────

function DashboardPage({ user }: { user: { email: string; full_name?: string | null } }) {
  const [analyses, setAnalyses] = useState<AnalysisSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const displayName = user.full_name ?? user.email.split("@")[0];

  useEffect(() => {
    listReports(1, 10)
      .then((res) => { setAnalyses(res.items); setTotal(res.total); })
      .catch(() => setError("Could not load analyses"))
      .finally(() => setLoading(false));
  }, []);

  const completed = analyses.filter((a) => a.status === "completed").length;
  const avgConf = avgScore(analyses, "confidence_score");
  const avgDur = avgDuration(analyses);

  const stats = [
    { icon: BarChart3, label: "Total Analyses", value: loading ? "—" : String(total), sub: "all time" },
    { icon: TrendingUp, label: "Completed", value: loading ? "—" : String(completed), sub: "successfully" },
    { icon: Shield, label: "Avg Confidence", value: loading ? "—" : avgConf, sub: "out of 100" },
    { icon: Clock, label: "Avg Duration", value: loading ? "—" : avgDur, sub: "per analysis" },
  ];

  return (
    <div style={{ padding: "32px 32px 64px" }}>
      <motion.div initial={fadeUp.initial} animate={fadeUp.animate} transition={fadeUp.transition} style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, color: "var(--text-primary)", letterSpacing: "-0.02em", marginBottom: 4 }}>
          Welcome back, {displayName}
        </h1>
        <p style={{ fontSize: 13, color: "var(--text-secondary)" }}>
          Board-level analysis powered by six specialised AI agents.
        </p>
      </motion.div>

      <motion.div variants={staggerContainer} initial="initial" animate="animate" style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginBottom: 28 }}>
        {stats.map(({ icon: Icon, label, value, sub }) => (
          <motion.div key={label} variants={staggerItem}>
            <Card hover padding="md">
              <div style={{ display: "flex", alignItems: "flex-start", gap: 12 }}>
                <div style={{ width: 36, height: 36, borderRadius: "var(--radius-md)", backgroundColor: "var(--accent-dim)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                  <Icon size={16} style={{ color: "var(--accent)" }} />
                </div>
                <div>
                  <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginBottom: 2, textTransform: "uppercase", letterSpacing: "0.04em" }}>{label}</div>
                  <div style={{ fontSize: 22, fontWeight: 700, color: "var(--text-primary)", lineHeight: 1.1 }}>{value}</div>
                  <div style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 2 }}>{sub}</div>
                </div>
              </div>
            </Card>
          </motion.div>
        ))}
      </motion.div>

      <motion.div initial={fadeUp.initial} animate={fadeUp.animate} transition={{ ...fadeUp.transition, delay: 0.15 }}>
        <Card padding="none">
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "16px 20px", borderBottom: "1px solid var(--border)" }}>
            <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>Recent Analyses</span>
            <Link href="/reports" style={{ fontSize: 12, color: "var(--accent)", textDecoration: "none", display: "flex", alignItems: "center", gap: 2 }}>
              View all <ChevronRight size={12} />
            </Link>
          </div>

          {loading && <div style={{ padding: "48px 20px", textAlign: "center", color: "var(--text-tertiary)", fontSize: 13 }}>Loading…</div>}

          {error && (
            <div style={{ padding: "48px 20px", textAlign: "center", color: "var(--danger)", fontSize: 13, display: "flex", flexDirection: "column", alignItems: "center", gap: 8 }}>
              <AlertCircle size={20} style={{ opacity: 0.7 }} />
              {error}
            </div>
          )}

          {!loading && !error && analyses.length === 0 && (
            <div style={{ padding: "64px 20px", textAlign: "center" }}>
              <FileText size={32} style={{ color: "var(--text-tertiary)", margin: "0 auto 12px", display: "block" }} />
              <p style={{ color: "var(--text-secondary)", fontSize: 13, marginBottom: 16 }}>No analyses yet.</p>
              <Link href="/analysis/new" style={{ display: "inline-flex", alignItems: "center", gap: 6, padding: "8px 16px", backgroundColor: "var(--accent)", color: "white", borderRadius: "var(--radius-md)", fontSize: 13, fontWeight: 500, textDecoration: "none" }}>
                <Plus size={14} />
                Start your first analysis
              </Link>
            </div>
          )}

          {!loading && analyses.length > 0 && (
            <div>
              {analyses.map((a, i) => (
                <Link key={a.id} href={`/analysis/${a.id}`} style={{ display: "flex", alignItems: "center", padding: "14px 20px", borderBottom: i < analyses.length - 1 ? "1px solid var(--border)" : "none", textDecoration: "none", transition: "background-color var(--transition-fast)" }}
                  onMouseEnter={(e) => { (e.currentTarget as HTMLAnchorElement).style.backgroundColor = "var(--bg-elevated)"; }}
                  onMouseLeave={(e) => { (e.currentTarget as HTMLAnchorElement).style.backgroundColor = "transparent"; }}
                >
                  <div style={{ marginRight: 12, flexShrink: 0 }}>
                    <StatusDot status={a.status === "completed" ? "done" : a.status === "running" ? "running" : a.status === "failed" ? "error" : "queued"} />
                  </div>
                  <div style={{ flex: 1, minWidth: 0, marginRight: 16 }}>
                    <p style={{ fontSize: 13, fontWeight: 500, color: "var(--text-primary)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{a.query}</p>
                    <p style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 2 }}>
                      {formatDistanceToNow(new Date(a.created_at), { addSuffix: true })}
                      {a.execution_time_ms != null && <span> · {(a.execution_time_ms / 1000).toFixed(0)}s</span>}
                    </p>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 12, flexShrink: 0 }}>
                    {a.confidence_score != null && (
                      <span style={{ fontSize: 11, color: a.confidence_score >= 80 ? "var(--success)" : a.confidence_score >= 65 ? "var(--warning)" : "var(--danger)", fontVariantNumeric: "tabular-nums", fontWeight: 600 }}>
                        {a.confidence_score.toFixed(0)}/100
                      </span>
                    )}
                    <StatusBadge status={a.status} />
                    <ChevronRight size={14} style={{ color: "var(--text-tertiary)" }} />
                  </div>
                </Link>
              ))}
            </div>
          )}
        </Card>
      </motion.div>
    </div>
  );
}

// ── Root page — smart routing ────────────────────────────────────────────────

export default function RootPage() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "var(--bg-base)" }}>
        <div style={{ width: 24, height: 24, borderRadius: "50%", border: "2px solid var(--border)", borderTopColor: "var(--accent)", animation: "spin 0.8s linear infinite" }} />
      </div>
    );
  }

  if (!user) {
    return <WelcomePage />;
  }

  return <DashboardPage user={user} />;
}

function avgScore(analyses: AnalysisSummary[], key: "confidence_score" | "data_quality_score"): string {
  const scores = analyses.map((a) => a[key]).filter((s): s is number => s != null);
  if (!scores.length) return "—";
  return (scores.reduce((a, b) => a + b, 0) / scores.length).toFixed(0);
}

function avgDuration(analyses: AnalysisSummary[]): string {
  const times = analyses.map((a) => a.execution_time_ms).filter((t): t is number => t != null);
  if (!times.length) return "—";
  return `${((times.reduce((a, b) => a + b, 0) / times.length) / 1000).toFixed(0)}s`;
}
