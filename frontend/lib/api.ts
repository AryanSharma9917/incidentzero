export const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");

export type RuntimeInfo = { execution_mode: "kubernetes" | "simulation"; runs_enabled: boolean; access_code_required: boolean; provider_configured: boolean; storage_ephemeral: boolean; daily_run_limit: number };

export type Incident = {
  id: string; scenario: string; created_at: string; latest_run_id: string | null; status: string;
  incident: { title: string; service: string; environment: string; severity: string; symptoms: string[] };
};
export type Evidence = { statement: string; source_type: string; source_url: string | null };
export type Run = {
  id: string; incident_id: string; status: "queued" | "running" | "verified" | "simulated" | "failed";
  created_at: string; finished_at: string | null; error: string | null;
  result: {
    execution_mode?: "kubernetes" | "simulation";
    root_cause?: string; root_cause_confidence?: number; supporting_evidence?: Evidence[];
    research_summary?: string; research_sources?: { url: string; title: string; excerpt: string; explanation: string }[];
    remediation_plan?: string; risk?: string; expected_outcome?: string; patch?: string; patch_diff?: string;
    iteration_count?: number; final_report?: string;
    cluster_context?: { pods: { name: string; phase: string; containers: { name: string; ready: boolean; restart_count: number; termination_reason: string | null; exit_code: number | null }[] }[]; logs: string; previous_logs: string | null; describe: string };
    validation_history?: { score: number; passed: boolean; checks: { name: string; passed: boolean; message: string }[] }[];
  };
};
export type RunEvent = { id: number; run_id: string; type: string; message: string; created_at: string };

export async function api<T>(path: string, method = "GET", signal?: AbortSignal): Promise<T> {
  const code = method !== "GET" && typeof window !== "undefined" ? sessionStorage.getItem("incidentzero.demoCode") : null;
  const response = await fetch(`${API_URL}${path}`, { method, headers: code ? { "X-Demo-Run-Token": code } : undefined, signal: signal || AbortSignal.timeout(15000), cache: "no-store" });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(typeof body.detail === "string" ? body.detail : `Request failed (${response.status})`);
  }
  return response.json();
}
