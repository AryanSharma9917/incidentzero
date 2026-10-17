import { test, expect } from "@playwright/test";

test.beforeEach(async ({ request }) => {
  const reset = await request.post("http://127.0.0.1:8100/__test__/reset");
  expect(reset.ok()).toBeTruthy();
});

test("persisted OOM workflow, diff, RCA export, replay, and mobile navigation", async ({ page }, testInfo) => {
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  await page.goto("/dashboard");
  await expect(page.getByText("No incidents yet.", { exact: false })).toBeVisible();
  await expect(page.getByRole("strong").filter({ hasText: /^0$/ })).toHaveCount(3);
  await page.getByRole("button", { name: "Create incident" }).click();
  await expect(page.getByRole("heading", { name: "Payment API pods are repeatedly restarting" })).toBeVisible();
  await page.getByRole("button", { name: "Start agent run" }).click();
  await expect(page.getByText("Sandbox fix verified.", { exact: false })).toBeVisible();
  await expect(page.getByRole("heading", { name: /Diagnosis.*99% confidence/ })).toBeVisible();
  await expect(page.getByLabel("Deployment patch diff")).toContainText("+            memory: 128Mi");
  await expect(page.getByText("PASS · http-health")).toBeVisible();
  await expect(page.getByText("run.completed", { exact: true })).toHaveCount(1);
  await page.screenshot({ path: testInfo.outputPath("run-desktop.png"), fullPage: true });
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("link", { name: "Download RCA · Markdown" }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toMatch(/^rca-.*\.md$/);
  await page.reload();
  await expect(page.getByText("Run complete · persisted history")).toBeVisible();
  await expect(page.getByText("run.completed", { exact: true })).toHaveCount(1);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole("link", { name: "Dashboard", exact: true }).click();
  await expect(page.getByText("Verified fixes", { exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "Payment API pods are repeatedly restarting", exact: true })).toBeVisible();
  expect(errors).toEqual([]);
});

test("failed runs show a terminal sanitized error when SSE is disconnected", async ({ page }) => {
  await page.route("**/stream?**", route => route.abort());
  await page.goto("/dashboard");
  await page.getByLabel("Failure scenario").selectOption("crashloop");
  await page.getByRole("button", { name: "Create incident" }).click();
  await page.getByRole("button", { name: "Start agent run" }).click();
  await expect(page.getByRole("alert").filter({ hasText: "Run failed." })).toContainText("Run failed. Check provider configuration");
  await expect(page.getByText("Run complete · persisted history")).toBeVisible();
  await expect(page.getByText("This run ended before an RCA could be generated.")).toBeVisible();
  await expect(page.locator("body")).not.toContainText("secret-token-must-not-leak");
  await expect(page.getByText("run.completed", { exact: true })).toHaveCount(1);
});


test("landing page architecture and safety remain usable on a narrow viewport", async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("verified fix");
  await expect(page.getByRole("heading", { name: "A small, inspectable system." })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Hosted simulation mode" })).toBeVisible();
  await expect(page.getByText("Production remains read-only", { exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
  await page.screenshot({ path: testInfo.outputPath("landing-mobile.png"), fullPage: true });
  await page.getByRole("link", { name: "Explore the incident workspace" }).click();
  await expect(page.getByRole("heading", { name: "Your incident command center" })).toBeVisible();
});

test("simulation results remain terminal and never count as Kubernetes verified fixes", async ({ page, request }) => {
  await request.post("http://127.0.0.1:8100/__test__/mode/simulation");
  await page.goto("/dashboard");
  await expect(page.getByText("Simulated infrastructure · live AI reasoning")).toBeVisible();
  await expect(page.getByText("Demo history is temporary", { exact: false })).toBeVisible();
  await page.getByLabel("Failure scenario").selectOption("readiness");
  await page.getByRole("button", { name: "Create incident" }).click();
  await page.getByRole("button", { name: "Start agent run" }).click();
  await expect(page.getByText("Simulation passed. This result is not a Kubernetes-verified fix.")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Simulated configuration validation" })).toBeVisible();
  await expect(page.getByText("Sandbox fix verified.", { exact: false })).toHaveCount(0);
  await page.getByRole("link", { name: "Dashboard", exact: true }).click();
  const verified = page.getByRole("article").filter({ has: page.getByText("Verified fixes", { exact: true }) });
  await expect(verified.getByRole("strong")).toHaveText("0");
  const active = page.getByRole("article").filter({ has: page.getByText("Active runs", { exact: true }) });
  await expect(active.getByRole("strong")).toHaveText("0");
});

test("operator pause disables mutation controls and keeps history readable", async ({ page, request }) => {
  await request.post("http://127.0.0.1:8100/__test__/mode/paused");
  await page.goto("/dashboard");
  await expect(page.getByText("Demo runs are paused by the operator.", { exact: false })).toBeVisible();
  await expect(page.getByRole("button", { name: "Create incident" })).toBeDisabled();
  await expect(page.getByText("No incidents yet.", { exact: false })).toBeVisible();
});

test("an access code unlocks writes without placing the code in URLs", async ({ page, request }) => {
  await request.post("http://127.0.0.1:8100/__test__/mode/protected");
  const requests: string[] = [];
  page.on("request", request => requests.push(request.url()));
  await page.goto("/dashboard");
  await page.getByRole("button", { name: "Create incident" }).click();
  await expect(page.getByRole("alert").filter({ hasText: "A valid demo access code" })).toBeVisible();
  await page.getByLabel("Demo access code", { exact: true }).fill("fixture-access-code");
  await page.getByRole("button", { name: "Use code", exact: true }).click();
  await page.getByRole("button", { name: "Create incident" }).click();
  await expect(page.getByRole("button", { name: "Start agent run" })).toBeVisible();
  expect(requests.every(url => !url.includes("fixture-access-code"))).toBeTruthy();
});
