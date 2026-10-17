"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { api, type Incident, type Run } from "@/lib/api";
import { metrics } from "@/lib/domain";
import { Alert, Empty, Status, Workspace } from "./workspace";

export function Overview({ view }: { view: "dashboard" | "incidents" | "runs" }) {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [runs, setRuns] = useState<Run[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [scenario, setScenario] = useState("oomkilled");
  const refresh = useCallback(async () => {
    try {
      const [incidentData, runData] = await Promise.all([api<Incident[]>("/api/incidents"), api<Run[]>("/api/runs")]);
      setIncidents(incidentData); setRuns(runData); setError("");
    } catch (err) { setError((err as Error).message); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { void refresh(); const timer = setInterval(() => void refresh(), 5000); return () => clearInterval(timer); }, [refresh]);
  async function createDemo() {
    setBusy(true); setError("");
    try {
      const incident = await api<Incident>(`/api/incidents/demo/${scenario}`, "POST");
      // Navigate to the persisted incident before starting a run, so a failed request never loses it.
      window.location.assign(`/incidents/${incident.id}`);
    } catch (err) { setError((err as Error).message); setBusy(false); }
  }
  const stats = metrics(runs);
  return <Workspace>
    <header className="page-heading"><div><p className="eyebrow">IncidentZero / {view}</p><h1>{view === "dashboard" ? "Your incident command center" : view === "incidents" ? "Incidents" : "Agent Runs"}</h1><p>Evidence, reasoning, and verified sandbox changes in one place.</p></div><button className="secondary" onClick={() => void refresh()}>Refresh</button></header>
    {error && <Alert message={error} />}
    {view === "dashboard" && <section className="metrics" aria-label="Stored demo history">
      {[["Total runs", stats.total], ["Verified fixes", stats.verified], ["Active runs", stats.active], ["Mean completed duration", stats.averageSeconds === null ? "—" : `${stats.averageSeconds}s`]].map(([label, value]) => <article key={label}><p>{label}</p><strong>{value}</strong><small>From stored demo history</small></article>)}
    </section>}
    {view !== "runs" && <section className="card demo-controls"><div><p className="eyebrow">Launch an investigation</p><h2>Create a demo incident</h2><p>Choose a reproducible fault. Starting its run will apply it only to the local Kind sandbox and use configured provider quota.</p></div><div><label htmlFor="scenario">Failure scenario</label><select id="scenario" value={scenario} onChange={event => setScenario(event.target.value)}><option value="oomkilled">OOMKilled · recommended</option><option value="crashloop">Configuration CrashLoop</option><option value="readiness">Readiness failure</option></select><button disabled={busy || stats.active > 0} onClick={() => void createDemo()}>{busy ? "Creating…" : "Create incident"}</button>{stats.active > 0 && <small>The shared sandbox has an active run.</small>}</div></section>}
    <section className="card"><h2>{view === "runs" ? "Execution history" : "Incident history"}</h2>
      {loading ? <p role="status">Loading persisted history…</p> : view === "runs" ? runs.length ? <div className="table-wrap"><table><thead><tr><th>Run</th><th>Status</th><th>Started</th><th>Attempts</th></tr></thead><tbody>{runs.map(run => <tr key={run.id}><td><Link href={`/runs/${run.id}`}>{run.id.slice(0, 8)}</Link></td><td><Status value={run.status} /></td><td>{new Date(run.created_at).toLocaleString()}</td><td>{run.result.iteration_count || "—"}</td></tr>)}</tbody></table></div> : <Empty>No agent runs yet. Create an incident to begin.</Empty> : incidents.length ? <div className="table-wrap"><table><thead><tr><th>Incident</th><th>Service</th><th>Severity</th><th>Status</th></tr></thead><tbody>{incidents.map(incident => <tr key={incident.id}><td><Link href={`/incidents/${incident.id}`}>{incident.incident.title}</Link><small>{incident.id.slice(0, 8)} · {incident.scenario}</small></td><td>{incident.incident.service}</td><td>{incident.incident.severity}</td><td><Status value={incident.status} /></td></tr>)}</tbody></table></div> : <Empty>No incidents yet. Your demo history will appear here.</Empty>}
    </section>
  </Workspace>;
}
