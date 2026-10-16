const workflow = ["Investigate", "Diagnose", "Research", "Repair", "Verify"];

export default function Home() {
  return (
    <main className="min-h-screen overflow-hidden bg-ink text-slate-100">
      <nav className="mx-auto flex max-w-7xl items-center justify-between px-6 py-7 lg:px-8" aria-label="Primary navigation">
        <a href="#top" className="font-mono text-sm font-semibold tracking-[0.16em] text-white">INCIDENT<span className="text-signal">ZERO</span></a>
        <div className="hidden items-center gap-8 text-sm text-slate-400 md:flex">
          <a className="transition hover:text-white" href="#workflow">How it works</a>
          <a className="transition hover:text-white" href="#safety">Safety</a>
          <span className="rounded-full border border-slate-700 px-3 py-1 font-mono text-xs text-slate-300">Foundation build</span>
        </div>
      </nav>

      <section id="top" className="relative mx-auto grid max-w-7xl gap-16 px-6 pb-24 pt-20 lg:grid-cols-[1.05fr_0.95fr] lg:px-8 lg:pb-32 lg:pt-28">
        <div className="relative z-10">
          <p className="mb-7 font-mono text-xs uppercase tracking-[0.25em] text-signal">Autonomous incident-resolution engineer</p>
          <h1 className="max-w-3xl text-5xl font-semibold leading-[1.04] tracking-[-0.04em] text-white sm:text-7xl">From incident to <span className="text-signal">verified fix.</span></h1>
          <p className="mt-7 max-w-xl text-lg leading-8 text-slate-400">IncidentZero investigates Kubernetes failures, determines root cause, proposes a controlled repair, and proves it works in a sandbox before a human approves it.</p>
          <div className="mt-10 flex flex-wrap items-center gap-4">
            <button disabled className="cursor-not-allowed rounded-lg bg-signal px-5 py-3 text-sm font-semibold text-ink opacity-70" title="Available in a later phase">Run demo incident</button>
            <span className="font-mono text-xs text-slate-500">Demo workflow arrives in Phase 2</span>
          </div>
        </div>

        <div className="relative lg:pt-3" aria-label="Agent workflow preview">
          <div className="absolute -inset-24 bg-[radial-gradient(circle,rgba(94,230,168,0.10),transparent_60%)]" />
          <div className="relative rounded-2xl border border-slate-800 bg-panel/95 p-5 shadow-panel">
            <div className="flex items-center justify-between border-b border-slate-800 pb-4">
              <div><p className="font-mono text-xs text-slate-500">INC-2026-0042</p><p className="mt-1 text-sm font-medium text-white">payment-api · demo-production</p></div>
              <span className="rounded-md bg-red-500/10 px-2.5 py-1 font-mono text-xs font-semibold text-red-400">P1</span>
            </div>
            <div className="space-y-1 pt-4">
              {workflow.map((step, index) => (
                <div key={step} className="flex items-center gap-4 rounded-lg px-3 py-3">
                  <span className={`grid h-7 w-7 place-items-center rounded-full border font-mono text-xs ${index === 0 ? "border-signal bg-signal/10 text-signal" : "border-slate-700 text-slate-500"}`}>{String(index + 1).padStart(2, "0")}</span>
                  <span className={index === 0 ? "text-sm text-white" : "text-sm text-slate-500"}>{step}</span>
                  {index === 0 && <span className="ml-auto font-mono text-[10px] uppercase tracking-wider text-signal">Ready</span>}
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section id="workflow" className="border-y border-slate-800 bg-slate-950/40">
        <div className="mx-auto grid max-w-7xl gap-px px-6 py-20 md:grid-cols-3 lg:px-8">
          {[
            ["01", "Evidence first", "Collect cluster state, events, logs, manifests, and resource signals before drawing conclusions."],
            ["02", "Reason and repair", "Use NVIDIA Nemotron to form hypotheses and generate a concrete, reviewable remediation."],
            ["03", "Verify before deploy", "Apply only to an isolated sandbox, evaluate health checks, and retry within strict bounds."],
          ].map(([number, title, copy]) => (
            <article key={number} className="border-l border-slate-800 px-6 first:border-l-0 md:px-8">
              <p className="font-mono text-xs text-signal">{number}</p><h2 className="mt-5 text-xl font-semibold text-white">{title}</h2><p className="mt-3 text-sm leading-6 text-slate-400">{copy}</p>
            </article>
          ))}
        </div>
      </section>

      <section id="safety" className="mx-auto max-w-7xl px-6 py-20 lg:px-8">
        <div className="flex flex-col justify-between gap-8 rounded-2xl border border-slate-800 bg-panel p-8 md:flex-row md:items-end">
          <div className="max-w-2xl"><p className="font-mono text-xs uppercase tracking-[0.2em] text-signal">Designed for control</p><h2 className="mt-4 text-3xl font-semibold tracking-tight text-white">Production remains read-only.</h2><p className="mt-4 leading-7 text-slate-400">Agent writes are restricted to a reproducible sandbox. Every proposed change remains visible, bounded, and subject to human approval.</p></div>
          <p className="font-mono text-xs text-slate-500">Nebius · NVIDIA · LangGraph · Tavily · Kubernetes</p>
        </div>
      </section>
    </main>
  );
}
