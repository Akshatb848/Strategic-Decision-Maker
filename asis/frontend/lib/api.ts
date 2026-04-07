/**
 * ASIS API client v3.0 — typed wrappers for all backend REST endpoints.
 * Uses /v1/ prefix, stores token in localStorage, throws ApiError on failure.
 */

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

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
  analysis_type?: "full" | "market" | "risk" | "financial";
  confidence_threshold?: number;
  use_rag?: boolean;
  use_memory?: boolean;
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
  rag_hits?: number | null;
  memory_hit?: boolean | null;
  progress?: number | null;
}

export interface AnalysisDetail extends AnalysisSummary {
  company_context: CompanyContext;
  agent_runs: AgentRunSummary[];
  strategic_brief: StrategicBrief | null;
  options?: AnalysisOptions;
}

export interface RoadmapPhase {
  phase: string;
  focus: string;
  key_actions: string[];
  investment: string;
  success_metric: string;
}

export interface BalancedScorecard {
  financial: string;
  customer: string;
  internal_process: string;
  learning_growth: string;
}

export interface StrategicBrief {
  executive_summary: string;
  strategic_imperatives: string[];
  roadmap: RoadmapPhase[];
  balanced_scorecard: BalancedScorecard;
  success_metrics: string[];
  decision_recommendation: "PROCEED" | "DEFER" | "REJECT" | "CONDITIONAL";
  overall_confidence: number;
  board_narrative: string;
  dissertation_contribution: string;
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

export interface UserProfile {
  id: string;
  email: string;
  role: string;
  full_name: string | null;
  organization: string | null;
  is_active: boolean;
  created_at: string;
}

export interface HealthResponse {
  status: string;
  version: string;
  agents_loaded?: number;
  rag_available?: boolean;
}

// ── ApiError ──────────────────────────────────────────────────────────────────

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}

// ── Token helpers ─────────────────────────────────────────────────────────────

const TOKEN_KEY = "asis_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  if (typeof window !== "undefined") {
    localStorage.setItem(TOKEN_KEY, token);
  }
}

export function clearToken(): void {
  if (typeof window !== "undefined") {
    localStorage.removeItem(TOKEN_KEY);
  }
}

function authHeaders(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// ── Core fetch wrapper ────────────────────────────────────────────────────────

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
      ...(options?.headers as Record<string, string> | undefined ?? {}),
    },
    ...options,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({})) as { detail?: string };
    throw new ApiError(res.status, body?.detail ?? res.statusText);
  }

  return res.json() as Promise<T>;
}

// ── Auth endpoints ────────────────────────────────────────────────────────────

export async function login(
  email: string,
  password: string
): Promise<TokenResponse> {
  return apiFetch<TokenResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function register(
  email: string,
  password: string,
  full_name?: string,
  organization?: string
): Promise<UserProfile> {
  return apiFetch<UserProfile>("/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password, full_name: full_name || null, organization: organization || null }),
  });
}

export async function getCurrentUser(): Promise<UserProfile> {
  return apiFetch<UserProfile>("/auth/me");
}

// ── Analysis endpoints ────────────────────────────────────────────────────────

export async function createAnalysis(
  request: CreateAnalysisRequest
): Promise<AnalysisSummary> {
  return apiFetch<AnalysisSummary>("/analysis", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export async function getAnalysis(id: string): Promise<AnalysisDetail> {
  return apiFetch<AnalysisDetail>(`/analysis/${id}`);
}

export async function listAnalyses(
  page = 1,
  pageSize = 20
): Promise<PaginatedAnalyses> {
  return apiFetch<PaginatedAnalyses>(
    `/analysis?page=${page}&page_size=${pageSize}`
  );
}

export async function cancelAnalysis(id: string): Promise<void> {
  await apiFetch(`/analysis/${id}/cancel`, { method: "POST" });
}

// ── Report endpoints ──────────────────────────────────────────────────────────

export async function listReports(
  page = 1,
  pageSize = 20
): Promise<PaginatedAnalyses> {
  return apiFetch<PaginatedAnalyses>(
    `/reports?page=${page}&page_size=${pageSize}`
  );
}

export async function getReport(analysisId: string): Promise<ReportSummary> {
  return apiFetch<ReportSummary>(`/reports/${analysisId}`);
}

export async function getEvaluation(
  analysisId: string
): Promise<EvaluationResponse> {
  return apiFetch<EvaluationResponse>(`/reports/${analysisId}/evaluation`);
}

// ── Export endpoints ──────────────────────────────────────────────────────────

export async function exportPdf(analysisId: string): Promise<Blob> {
  const token = getToken();
  const res = await fetch(`${API_BASE}/reports/${analysisId}/export/pdf`, {
    headers: {
      Accept: "application/pdf",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });
  if (!res.ok) throw new ApiError(res.status, "Export failed");
  return res.blob();
}

export async function exportDocx(analysisId: string): Promise<Blob> {
  const token = getToken();
  const res = await fetch(
    `${API_BASE}/reports/${analysisId}/export/docx`,
    {
      headers: {
        Accept:
          "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    }
  );
  if (!res.ok) throw new ApiError(res.status, "Export failed");
  return res.blob();
}

// ── Health endpoint ───────────────────────────────────────────────────────────

export async function getHealth(): Promise<HealthResponse> {
  return apiFetch<HealthResponse>("/health");
}
