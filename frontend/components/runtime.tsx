"use client";
import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { api, type RuntimeInfo } from "@/lib/api";

const RuntimeContext = createContext<{ runtime: RuntimeInfo | null; error: string }>({ runtime: null, error: "" });
export const useRuntime = () => useContext(RuntimeContext);

export function RuntimeProvider({ children }: { children: ReactNode }) {
  const [runtime, setRuntime] = useState<RuntimeInfo | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    async function load() {
      try { const info = await api<RuntimeInfo>("/api/runtime"); if (active) { setRuntime(info); setError(""); } }
      catch { if (active) setError("Cannot reach demo configuration. The service may be starting; retrying shortly."); }
    }
    void load();
    const timer = setInterval(() => void load(), 15000);
    return () => { active = false; clearInterval(timer); };
  }, []);
  return <RuntimeContext.Provider value={{ runtime, error }}>{children}</RuntimeContext.Provider>;
}

export function RuntimeBanner() {
  const { runtime, error } = useRuntime();
  const [code, setCode] = useState("");
  const [saved, setSaved] = useState(false);
  if (error) return <p role="alert" className="error-box">{error}</p>;
  if (!runtime) return <p role="status" className="runtime-banner">Connecting to demo service…</p>;
  return <section className="runtime-banner" aria-label="Demo environment">
    <strong>{runtime.execution_mode === "simulation" ? "Simulated infrastructure · live AI reasoning" : "Local Kubernetes sandbox"}</strong>
    <p>{runtime.execution_mode === "simulation" ? "Cluster evidence and validation are simulated. Nemotron generates the diagnosis and patch; no Kubernetes changes or live health checks run here." : "Evidence and validation use the controlled local Kind cluster. Production remains read-only."}</p>
    {runtime.storage_ephemeral && <p>Demo history is temporary and may reset when the hosting service restarts. Download the RCA to keep a copy.</p>}
    {!runtime.runs_enabled ? <p>Demo runs are paused by the operator. Saved history remains available.</p> : !runtime.provider_configured && <p>The reasoning provider is not configured yet. The operator must configure it before a run can complete.</p>}
    {runtime.access_code_required && runtime.runs_enabled && <form onSubmit={event => { event.preventDefault(); sessionStorage.setItem("incidentzero.demoCode", code); setSaved(true); setCode(""); }}>
      <label htmlFor="demo-code">Demo access code</label><div><input id="demo-code" type="password" autoComplete="off" value={code} onChange={event => { setCode(event.target.value); setSaved(false); }} /><button type="submit" disabled={!code}>Use code</button><button type="button" className="secondary" onClick={() => { sessionStorage.removeItem("incidentzero.demoCode"); setSaved(false); }}>Clear code</button></div><small role="status">{saved ? "Access code saved for this tab. You can now start a demo." : "Use the code shared by the operator. It stays in this browser tab."}</small>
    </form>}
  </section>;
}
