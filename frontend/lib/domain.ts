import type { Run, RunEvent } from "./api";

export function metrics(runs: Run[]) {
  const completed = runs.filter(run => run.status === "verified" || run.status === "simulated" || run.status === "failed");
  const durations = completed.filter(run => run.finished_at).map(run =>
    Math.max(0, (Date.parse(run.finished_at!) - Date.parse(run.created_at)) / 1000));
  return {
    total: runs.length,
    active: runs.length - completed.length,
    verified: runs.filter(run => run.status === "verified").length,
    averageSeconds: durations.length ? Math.round(durations.reduce((a, b) => a + b, 0) / durations.length) : null,
  };
}

export function mergeEvents(existing: RunEvent[], incoming: RunEvent[]) {
  return [...new Map([...existing, ...incoming].map(event => [event.id, event])).values()].sort((a, b) => a.id - b.id);
}

export function isTerminal(run: Run) {
  return run.status === "verified" || run.status === "simulated" || run.status === "failed";
}
