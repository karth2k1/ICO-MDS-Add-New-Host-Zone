const { test, expect } = require("@playwright/test");
const { submitOpenApiGeneration } = require("../helpers/openapi");

test.describe("ICO UI smoke", () => {
  test("mode switch behavior and UCSD disabled state", async ({ page }) => {
    await page.goto("/");

    await expect(page.getByTestId("mode-ucsd")).toBeDisabled();
    await expect(page.locator("#requirements-group")).toBeVisible();
    await expect(page.locator("#openapi-group")).toBeHidden();

    await page.getByTestId("mode-openapi").check();
    await expect(page.locator("#openapi-group")).toBeVisible();
    await expect(page.locator("#requirements-group")).toBeHidden();

    await page.getByTestId("mode-requirements").check();
    await expect(page.locator("#requirements-group")).toBeVisible();
  });

  test("openapi generation succeeds with bounded operations", async ({ page }) => {
    await page.goto("/");
    const { response, payload } = await submitOpenApiGeneration(page, {
      maxOperations: 2,
      includeSampleWorkflow: false,
    });

    expect(response.status()).toBe(200);
    expect(payload.success).toBeTruthy();
    expect(payload.analysis.workflow_type).toBe("openapi");
    expect(payload.analysis.generated_operations).toBeLessThanOrEqual(2);

    await expect(page.getByTestId("output-section")).toBeVisible();
    await expect(page.getByTestId("error-container")).toBeHidden();
  });

  test("openapi invalid filter path shows actionable error", async ({ page }) => {
    await page.goto("/");
    const { response, payload } = await submitOpenApiGeneration(page, {
      maxOperations: 5,
      pathPrefix: "/path/that/will/not/match",
      includeSampleWorkflow: false,
    });

    expect(response.status()).toBe(400);
    expect(payload.error).toContain("No API operations matched");
    await expect(page.getByTestId("error-container")).toBeVisible();
  });
});
