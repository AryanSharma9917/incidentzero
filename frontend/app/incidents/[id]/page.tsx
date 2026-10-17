"use client";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, type Incident, type Run } from "@/lib/api";
import { Alert, Status, Workspace } from "@/components/workspace";

export default function IncidentDetail() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [incident, setIncident] = useState<Incident | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => { api<Incident>(`/api/incidents/${id}`).then(setIncident).catch(err => setError(err.message)); }, [id]);
  async function start() {
    setBusy(true); setError("");
    try { const run = await api<Run>(`/api/incidents/${id}/run`, "POST"); router.push(`/runs/${run.id}`); }
    catch (err) { setError((err as Error).message); setBusy(false); }
  }
  return <Workspace><Link className="back-link" href="/incidents">← Incidents</Link>{error && <Alert message={error} />}
    {incident ? <><header className="page-heading"><div><p className="eyebrow">{incident.id}</p><h1>{incident.incident.title}</h1><p>{incident.incident.service} · {incident.incident.environment} · {incident.incident.severity}</p></div><Status value={incident.status} /></header><section className="card"><h2>Observed symptoms</h2><ul>{incident.incident.symptoms.map(symptom => <li key={symptom}>{symptom}</li>)}</ul><p>Scenario: {incident.scenario}. Evidence will be collected from Kubernetes when the run starts.</p><p>Starting a run applies this fault in the controlled local Kind sandbox and uses configured Nebius/Nemotron quota. Tavily is called only if research is needed.</p><button disabled={busy} onClick={() => void start()}>{busy ? "Starting…" : "Start agent run"}</button>{incident.latest_run_id && <Link className="inline-link" href={`/runs/${incident.latest_run_id}`}>View latest run →</Link>}</section></> : !error && <p role="status">Loading incident…</p>}
  </Workspace>;
}
