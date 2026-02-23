const path = require("path");
const { expect } = require("@playwright/test");
const { normalizeOpenApiOptions } = require("../../automation-core/src");

function fixturePath(name) {
  return path.resolve(__dirname, "..", "fixtures", name);
}

async function switchToOpenApiMode(page) {
  await page.getByTestId("mode-openapi").check();
  await expect(page.locator("#openapi-group")).toBeVisible();
}

async function submitOpenApiGeneration(page, options = {}) {
  const { fixture, maxOperations, pathPrefix, tag, includeSampleWorkflow } =
    normalizeOpenApiOptions(options);

  await switchToOpenApiMode(page);
  await page.getByTestId("openapi-file").setInputFiles(fixturePath(fixture));
  await page.getByTestId("openapi-max-ops").fill(String(maxOperations));
  await page.getByTestId("openapi-path-prefix").fill(pathPrefix);
  await page.getByTestId("openapi-tag").fill(tag);

  const includeCheckbox = page.getByTestId("openapi-include-workflow");
  if (includeSampleWorkflow) {
    await includeCheckbox.check();
  } else {
    await includeCheckbox.uncheck();
  }

  const responsePromise = page.waitForResponse((response) =>
    response.url().includes("/generate/openapi") && response.request().method() === "POST"
  );
  await page.getByTestId("generate-btn").click();
  const response = await responsePromise;
  const payload = await response.json();
  return { response, payload };
}

module.exports = {
  fixturePath,
  submitOpenApiGeneration,
  switchToOpenApiMode,
};
