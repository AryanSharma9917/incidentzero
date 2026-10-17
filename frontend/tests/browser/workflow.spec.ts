import { test, expect } from "@playwright/test";

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
