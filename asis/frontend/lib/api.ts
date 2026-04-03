/**
 * ASIS API client — typed wrappers around all backend REST endpoints.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface CompanyContext {
  company_name: string;
  sector: string;
  target_market: string;
  hq_country?: string;
  annual_revenue_usd_mn?: number;
  employee_count?: number;
  additional_context?: string;
}

export interface AnalysisOptions {
  include_financial?: boolean;
  include_competitor?: boolean;
  include_market?: boolean;
  include_risk?: boolean;
  run_baseline?: boolean;
}

export interface CreateAnalysisRequest {
  query: string;
  company_context: CompanyContext;
  options?: AnalysisOptions;
}

export interface AnalysisSummary {
  id: string;
  query: string;
  status: "pending" | "running" | "completed" | "failed";
  created_at: string;
  completed_at: string | null;
  execution_time_ms: number | null;
  confidence_score: number | null;
  data_quality_score: number | null;
}

export interface AgentRunSummary {
  agent_name: string;
  status: "idle" | "running" | "completed" | "error" | "skipped";
  tokens_used: number | null;
  duration_ms: number | null;
  error_message: string | null;
}

export interface AnalysisDetail extends AnalysisSummary {
  company_context: CompanyContext;
  agent_runs: AgentRunSummary[];
  strategic_brief: StrategicBrief | null;
}

export interface StrategicOption {
  option_id: string;
  title: string;
  description: string;
  rationale: string;
  pros: string[];
  cons: string[];
  estimated_investment_usd_mn: number | null;
  time_to_value: string;
  risk_level: "low" | "medium" | "high";
  recommended: boolean;
}

export interface NextStep {
  priority: number;
  action: string;
  owner: string;
  timeline: string;
  success_criteria: string;
}

export interface StrategicBrief {
  executive_summary: string;
  recommendation: string;
  strategic_options: StrategicOption[];
  risk_summary: string;
  financial_summary: string;
  market_summary: string;
  competitive_summary: string;
  next_steps: NextStep[];
  confidence_score: number;
  data_quality_score: number;
  caveats: string[];
  sources: string[];
}

export interface ReportSummary {
  id: string;
  analysis_id: string;
  confidence_score: number | null;
  data_quality_score: number | null;
  sources_count: number | null;
  eval_overall_score: number | null;
  created_at: string;
}

export interface EvaluationResponse {
  analysis_id: string;
  analytical_depth: number | null;
  factual_accuracy: number | null;
  contextual_relevance: number | null;
  actionability: number | null;
  internal_consistency: number | null;
  overall_score: number | null;
  baseline_overall_score: number | null;
  improvement_over_baseline: number | null;
}

export interface PaginatedAnalyses {
  items: AnalysisSummary[];
  total: number;
  page: number;
  page_size: number;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

// ── Auth helpers ──────────────────────────────────────────────────────────────

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("asis_token");
}

export function setToken(token: string): void {
  localStorage.setItem("asis_token", token);
}

export function clearToken(): void {
  localStorage.removeItem("asis_token");
}

function authHeaders(): HeadersInit {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// ── Core fetch wrapper ────────────────────────────────────────────────────────

async function apiFetch<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
      ...(options?.headers ?? {}),
    },
    ...options,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, body?.detail ?? res.statusText);
  }

  return res.json() as Promise<T>;
}

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}

// ── Auth endpoints ────────────────────────────────────────────────────────────

export async function login(email: string, password: string): Promise<TokenResponse> {
  return apiFetch<TokenResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function register(email: string, password: string): Promise<void> {
  await apiFetch("/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

// ── Analysis endpoints ────────────────────────────────────────────────────────

export async function getAnalysis(id: string): Promise<AnalysisDetail> {
  return apiFetch<AnalysisDetail>(`/analysis/${id}`);
}

// ── Report endpoints ──────────────────────────────────────────────────────────

export async function listReports(
  page = 1,
  pageSize = 20
): Promise<PaginatedAnalyses> {
  return apiFetch<PaginatedAnalyses>(`/reports?page=${page}&page_size=${pageSize}`);
}

export async function getReport(analysisId: string): Promise<ReportSummary> {
  return apiFetch<ReportSummary>(`/reports/${analysisId}`);
}

export async function getEvaluation(analysisId: string): Promise<EvaluationResponse> {
  return apiFetch<EvaluationResponse>(`/reports/${analysisId}/evaluation`);
}

// ── Health endpoint ───────────────────────────────────────────────────────────

export async function getHealth(): Promise<{ status: string; version: string }> {
  return apiFetch<{ status: string; version: string }>("/health");
}
