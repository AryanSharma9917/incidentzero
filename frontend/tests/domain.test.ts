import assert from "node:assert/strict";
import test from "node:test";
import { metrics, mergeEvents, isTerminal } from "../lib/domain.ts";
import type { Run, RunEvent } from "../lib/api.ts";

const run = (overrides: Partial<Run>): Run => ({ id: "run", incident_id: "inc", status: "queued", created_at: "2026-10-17T10:00:00Z", finished_at: null, result: {}, error: null, ...overrides });
test("empty history has zero counts and no invented duration", () => {
  assert.deepEqual(metrics([]), { total: 0, active: 0, verified: 0, averageSeconds: null });
});
test("metrics derive durations and counts from both successful and failed history", () => {
  assert.deepEqual(metrics([
    run({ status: "verified", finished_at: "2026-10-17T10:00:30Z" }),
    run({ status: "failed", finished_at: "2026-10-17T10:01:00Z" }),
    run({ status: "running" }), run({ status: "queued" }),
  ]), { total: 4, active: 2, verified: 1, averageSeconds: 45 });
});
test("SSE replay and polling merge into a stable timeline without duplicates", () => {
  const event = (id: number): RunEvent => ({ id, run_id: "run", type: "validation.check", message: String(id), created_at: "now" });
  assert.deepEqual(mergeEvents([event(2), event(1)], [event(2), event(3)]).map(item => item.id), [1, 2, 3]);
});
test("both terminal states end live loading", () => {
  assert.equal(isTerminal(run({ status: "verified" })), true);
  assert.equal(isTerminal(run({ status: "failed" })), true);
  assert.equal(isTerminal(run({ status: "running" })), false);
  assert.equal(isTerminal(run({ status: "queued" })), false);
});
