const { defineConfig, devices } = require("@playwright/test");

module.exports = defineConfig({
  testDir: "./e2e/tests",
  timeout: 120000,
  expect: {
    timeout: 15000,
  },
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [
    ["list"],
    ["html", { outputFolder: "e2e/reports/html", open: "never" }],
    ["junit", { outputFile: "e2e/reports/junit/results.xml" }],
  ],
  use: {
    baseURL: process.env.E2E_BASE_URL || "http://127.0.0.1:5080",
    trace: "on-first-retry",
    video: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  webServer: {
    command: "FLASK_DEBUG=0 python3 run.py",
    url: "http://127.0.0.1:5080/status",
    reuseExistingServer: true,
    cwd: __dirname,
    timeout: 120000,
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
