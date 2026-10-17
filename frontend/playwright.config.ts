import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/browser",
  workers: 1,
  retries: 0,
  use: {
    baseURL: "http://127.0.0.1:3100",

  },
  projects: [
    { name: "chromium", use: { browserName: "chromium", launchOptions: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE ? { executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE } : {} } },
    { name: "firefox", use: { browserName: "firefox" } },
    { name: "webkit", use: { browserName: "webkit" } },
  ],
  webServer: [
    {
      command: "UI_TEST_DATABASE_PATH=$(mktemp -d /tmp/incidentzero-ui.XXXXXX)/history.sqlite3 PYTHONPATH=.:tests .venv/bin/uvicorn tests.ui_fixture:app --host 127.0.0.1 --port 8100",
      cwd: "../backend", url: "http://127.0.0.1:8100/health", reuseExistingServer: false,
    },
    {
      command: "NEXT_PUBLIC_API_URL=http://127.0.0.1:8100 npm run dev -- --hostname 127.0.0.1 --port 3100",
      url: "http://127.0.0.1:3100", reuseExistingServer: false,
    },
  ],
});
