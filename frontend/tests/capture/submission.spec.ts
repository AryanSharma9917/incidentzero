import { test, expect } from "@playwright/test";
import { mkdir, readFile, writeFile, rm } from "node:fs/promises";
import path from "node:path";

test("capture explicitly mocked submission rehearsal", async ({ browser, request }) => {
  const root = path.resolve("../docs/assets");
  const shots = path.join(root, "screenshots");
  await mkdir(shots, { recursive: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 960 },
    recordVideo: { dir: path.join(root, "recording-tmp"), size: { width: 1440, height: 960 } } });
  await context.addInitScript(() => {
    document.addEventListener("DOMContentLoaded", () => {
      const label = document.createElement("div");
      label.id = "rehearsal-label";
      label.textContent = "LOCAL UI REHEARSAL · MOCKED NEMOTRON / TAVILY + KUBERNETES · NOT LIVE ACCEPTANCE";
      label.style.cssText = "position:fixed;top:0;left:0;right:0;z-index:2147483647;background:#402c0b;color:#ffdf8d;font:600 13px/40px monospace;text-align:center;border-bottom:1px solid #ad8030";
      document.body.style.paddingTop = "40px";
      document.body.appendChild(label);
    });
  });
  const page = await context.newPage();
  const video = page.video()!;
  const entries: { file: string; subject: string; provenance: string; width: number; height: number }[] = [];
  async function caption(text: string) {
    await page.evaluate(text => {
      let element = document.getElementById("rehearsal-caption");
      if (!element) { element = document.createElement("div"); element.id = "rehearsal-caption"; document.body.appendChild(element); }
      element.textContent = text;
      element.style.cssText = "position:fixed;bottom:18px;left:12%;right:12%;z-index:2147483646;background:#07101ff2;border:1px solid #55718d;border-radius:8px;color:#e2eefb;font:16px/1.6 system-ui;padding:15px 22px;text-align:center";
    }, text);
  }
  async function capture(file: string, subject: string, holdMs: number) {
    await expect(page.locator("#rehearsal-label")).toBeVisible();
    await page.locator("#rehearsal-caption").evaluateAll(elements => elements.forEach(element => element.remove()));
    await page.screenshot({ path: path.join(shots, file), animations: "disabled" });
    entries.push({ file: `screenshots/${file}`, subject, provenance: "mocked-ui-rehearsal", width: 1440, height: 960 });
    await caption(subject);
    await page.waitForTimeout(holdMs);
  }
  await page.goto("/");
  await capture("01-landing.png", "IncidentZero investigates Kubernetes incidents. This recording uses mocked external boundaries; live provider and five-run acceptance remain pending.", 12000);
  await page.goto("/dashboard");
  await expect(page.getByRole("button", { name: "Create incident" })).toBeEnabled();
  await capture("02-dashboard.png", "History and metrics come from persisted runs. The production architecture uses FastAPI, SQLite, Server-Sent Events, and LangGraph.", 12000);
  await page.getByRole("button", { name: "Create incident" }).click();
  await expect(page.getByRole("heading", { name: "Payment API pods are repeatedly restarting" })).toBeVisible();
  await capture("03-incident.png", "The OOMKilled golden path starts with payment-api. Real execution collects pods, events, resources, and current/previous logs.", 14000);
  await page.getByRole("button", { name: "Start agent run" }).click();
  await expect(page.getByText("Run complete · persisted history")).toBeVisible();
  await page.locator(".timeline-card").scrollIntoViewIfNeeded();
  await capture("04-timeline.png", "The agent timeline persists every stage. In a live run, NVIDIA Nemotron through Nebius Token Factory generates hypotheses and a final diagnosis.", 18000);
  await page.getByRole("heading", { name: /Diagnosis.*confidence/ }).scrollIntoViewIfNeeded();
  await capture("05-diagnosis.png", "This fixture diagnosis is mocked. The real integration validates structured model output, confidence, evidence, and citations with one bounded repair attempt.", 18000);
  await page.getByRole("heading", { name: "Research sources", exact: true }).scrollIntoViewIfNeeded();
  await expect(page.getByRole("link", { name: /Kubernetes resource management/ })).toBeVisible();
  await capture("06-research.png", "Tavily is conditional. This fixture illustrates compact, attributable sources; it does not represent a live Tavily request.", 16000);
  await page.getByLabel("Deployment patch diff").scrollIntoViewIfNeeded();
  await capture("07-remediation-diff.png", "A concrete YAML patch must pass the deterministic allow-list. No model-generated shell commands are executed; remediation is bounded to two attempts.", 18000);
  await page.getByRole("heading", { name: "Sandbox validation", exact: true }).scrollIntoViewIfNeeded();
  await capture("08-validation.png", "Validation here is mocked. Local Kind mode performs real rollout, owned-pod, restart, log, and HTTP health checks. Hosted simulation is labeled separately.", 18000);
  await page.getByRole("heading", { name: "Root cause report" }).scrollIntoViewIfNeeded();
  await caption("Export the RCA for human review. No production changes are applied. Next: live provider/Kind acceptance, public deployment, and five recorded successful OOM runs.");
  await page.waitForTimeout(12000);
  const runs = await request.get("http://127.0.0.1:8100/api/runs");
  const run = (await runs.json())[0];
  await writeFile(path.join(root, "rehearsal-rca.md"), "> MOCKED UI REHEARSAL: all model, search, and Kubernetes evidence below is fixture output, not live acceptance.\n\n" + run.result.final_report);
  await context.close();
  await video.saveAs(path.join(root, "rehearsal.webm"));
  await rm(path.join(root, "recording-tmp"), { recursive: true, force: true });
  const diagram = await browser.newPage({ viewport: { width: 1440, height: 960 } });
  await diagram.setContent("<style>body{margin:0}</style>" + await readFile(path.join(root, "architecture.svg"), "utf8"));
  await diagram.screenshot({ path: path.join(root, "architecture.png") });
  await diagram.close();
  await writeFile(path.join(root, "capture-manifest.json"), JSON.stringify({ captured_at: new Date().toISOString(),
    provenance: "mocked-ui-rehearsal", reasoning: "mocked", research: "mocked", infrastructure: "mocked",
    video: "rehearsal.webm", video_status: "captioned silent rehearsal; not final live demo", screenshots: entries }, null, 2) + "\n");
});
