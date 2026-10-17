"use client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { api, API_URL, type Run, type RunEvent } from "@/lib/api";
import { isTerminal, mergeEvents } from "@/lib/domain";
import { Alert, Empty, Status, Workspace } from "@/components/workspace";

const eventTypes = ["incident.received", "demo.started", "demo.completed", "context.started", "context.completed", "diagnosis.started", "diagnosis.completed", "research.started", "research.completed", "synthesis.started", "synthesis.completed", "remediation.started", "remediation.generated", "remediation.failed", "validation.started", "validation.check", "validation.failed", "validation.completed", "report.generated", "run.error", "run.completed"];

export default function RunDetail() {
  const { id } = useParams<{ id: string }>();
  const [run, setRun] = useState<Run | null>(null);
  const [events, setEvents] = useState<RunEvent[]>([]);
  const [error, setError] = useState("");
  const [connection, setConnection] = useState("Connecting to live events…");
  useEffect(() => {
    let disposed = false;
    let source: EventSource | undefined;
    let terminal = false;
    let cursor = 0;
    let refreshing = false;
    setRun(null); setEvents([]); setError("");
    async function refresh() {
      if (refreshing || disposed) return;
      refreshing = true;
      try {
        const [data, history] = await Promise.all([api<Run>(`/api/runs/${id}`), api<RunEvent[]>(`/api/runs/${id}/events?after=${cursor}`)]);
        if (disposed) return;
        setRun(data); setEvents(existing => mergeEvents(existing, history));
        cursor = Math.max(cursor, ...history.map(event => event.id));
        setError("");
        if (isTerminal(data)) { terminal = true; source?.close(); setConnection("Run complete · persisted history"); }
      } catch (err) { if (!disposed) setError(`${(err as Error).message}. Retrying every 3 seconds.`); }
      finally { refreshing = false; }
    }
    void refresh().then(() => {
      if (disposed || terminal) return;
      source = new EventSource(`${API_URL}/api/runs/${id}/stream?after=${cursor}`);
      source.onopen = () => { if (!disposed) setConnection("Live event stream connected"); };
      source.onerror = () => { if (!disposed && !terminal) setConnection("Stream reconnecting · refreshing saved progress every 3 seconds"); };
      source.addEventListener("stream.error", () => { source?.close(); if (!disposed) setConnection("Stream unavailable · refreshing saved progress every 3 seconds"); });
      for (const type of eventTypes) source.addEventListener(type, event => {
        if (disposed) return;
        try {
          const entry = JSON.parse((event as MessageEvent).data) as RunEvent;
          // The stream may catch up before REST refresh completes; merge by event ID.
          setEvents(existing => mergeEvents(existing, [entry]));
          void refresh();
        } catch { setConnection("Invalid stream event · refreshing saved progress"); }
      });
    });
    const timer = setInterval(() => { if (!terminal) void refresh(); }, 3000);
    return () => { disposed = true; clearInterval(timer); source?.close(); };
  }, [id]);
  const result = run?.result;
  const simulated = result?.execution_mode === "simulation";
  return <Workspace><Link className="back-link" href="/runs">← Agent Runs</Link>
    {error && <Alert message={error} />}
    {run && result ? <>
      <header className="page-heading"><div><p className="eyebrow">Run {run.id.slice(0, 8)}</p><h1>Investigation & resolution</h1><p>Started {new Date(run.created_at).toLocaleString()} · Attempt {result.iteration_count || 0} of 2</p><Link href={`/incidents/${run.incident_id}`}>View incident →</Link></div><Status value={run.status} /></header>
      {run.error && <Alert message={run.error} />}
      {simulated && <div className="simulation-box">Simulated infrastructure: evidence and validation are configuration simulations. No Kubernetes rollout or live health check was performed.</div>}
      {run.status === "simulated" && <div className="simulation-box">Simulation passed. This result is not a Kubernetes-verified fix.</div>}
      {run.status === "verified" && <div className="success-box">Sandbox fix verified. Human approval is required before any production change.</div>}
      <div className="run-grid"><section className="card timeline-card"><p className="eyebrow">Agent activity</p><h2>Execution timeline</h2><p className="connection" role="status">{connection}</p><ol className="timeline">{events.map(event => <li key={event.id}><time>{new Date(event.created_at).toLocaleTimeString()}</time><strong>{event.type}</strong><p>{event.message}</p></li>)}</ol>{!events.length && <Empty>Waiting for saved events.</Empty>}</section>
      <div className="result-stack">
        <section className="card"><p className="eyebrow">01 / Observe</p><h2>{simulated ? "Simulated infrastructure evidence" : "Kubernetes evidence"}</h2><p>Evidence collected before remediation. Validation results appear below.</p>{result.cluster_context ? <>
          {result.cluster_context.pods.map(pod => <article className="pod" key={pod.name}><h3>{pod.name} · {pod.phase}</h3>{pod.containers.map(container => <p key={container.name}>{container.name}: {container.ready ? "Ready" : "Unready"} · {container.restart_count} restarts{container.termination_reason && ` · ${container.termination_reason} / exit ${container.exit_code}`}</p>)}</article>)}
          <details><summary>Current and previous application logs</summary><pre>{result.cluster_context.logs || "No current logs"}{"\n\nPrevious logs:\n"}{result.cluster_context.previous_logs || "No previous logs"}</pre></details>
          <details><summary>Pod description and events</summary><pre>{result.cluster_context.describe}</pre></details>
        </> : <Empty>Cluster evidence has not been collected.</Empty>}</section>
        <section className="card"><p className="eyebrow">02 / Reason</p><h2>Diagnosis {result.root_cause_confidence !== undefined && <span className="confidence">{Math.round(result.root_cause_confidence * 100)}% confidence</span>}</h2>{result.root_cause ? <><p className="diagnosis">{result.root_cause}</p><ul>{result.supporting_evidence?.map((evidence, i) => <li key={i}>{evidence.statement}{evidence.source_url && <> <a href={evidence.source_url} target="_blank" rel="noreferrer">Source ↗</a></>}</li>)}</ul></> : <Empty>No final diagnosis yet.</Empty>}</section>
        <section className="card"><h2>Research sources</h2><p>{result.research_summary || "Tavily research runs only when Nemotron requests it."}</p>{result.research_sources?.map(source => <article className="source" key={source.url}><a href={source.url} target="_blank" rel="noreferrer">{source.title} ↗</a><p>{source.excerpt}</p><small>{source.explanation}</small></article>)}</section>
        <section className="card"><p className="eyebrow">03 / Repair</p><h2>Proposed remediation</h2>{result.patch ? <><p>{result.remediation_plan}</p><p>Risk: {result.risk}. Expected: {result.expected_outcome}</p>{result.patch_diff ? <pre className="diff" aria-label="Deployment patch diff">{result.patch_diff.split("\n").map((line, index) => <span key={index} className={line.startsWith("+") ? "added" : line.startsWith("-") ? "removed" : ""}>{line}{"\n"}</span>)}</pre> : <pre>{result.patch}</pre>}<details><summary>Strategic merge patch</summary><pre>{result.patch}</pre></details></> : <Empty>No policy-approved patch yet.</Empty>}</section>
        <section className="card"><p className="eyebrow">04 / Verify</p><h2>{simulated ? "Simulated configuration validation" : "Sandbox validation"}</h2>{result.validation_history?.length ? result.validation_history.map((validation, index) => <article key={index} className="validation"><h3>Attempt {index + 1} <Status value={validation.passed ? simulated ? "simulated" : "verified" : "failed"} /> <span>{validation.score}/100{simulated ? " · simulation" : ""}</span></h3><ul>{validation.checks.map((check, i) => <li key={i}><strong className={check.passed ? "check-pass" : "check-fail"}>{check.passed ? "PASS" : "FAIL"} · {check.name}</strong><p>{check.message}</p></li>)}</ul></article>) : <Empty>No sandbox checks completed.</Empty>}</section>
        <section className="card"><h2>Root cause report</h2>{result.final_report ? <><a className="button-link" href={`${API_URL}/api/runs/${id}/report`}>Download RCA · Markdown</a><details><summary>Read report</summary><pre>{result.final_report}</pre></details></> : <Empty>{isTerminal(run) ? "This run ended before an RCA could be generated." : "The RCA appears when the workflow finishes."}</Empty>}</section>
      </div></div>
    </> : !error && <p role="status">Loading run…</p>}
  </Workspace>;
}
