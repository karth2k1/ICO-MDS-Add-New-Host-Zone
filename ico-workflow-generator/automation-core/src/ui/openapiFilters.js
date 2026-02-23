function normalizeOpenApiOptions(options = {}) {
  return {
    fixture: options.fixture || "sample_openapi_minimal.yaml",
    maxOperations: String(options.maxOperations ?? "50"),
    pathPrefix: options.pathPrefix || "",
    tag: options.tag || "",
    includeSampleWorkflow: options.includeSampleWorkflow !== false,
  };
}

module.exports = {
  normalizeOpenApiOptions,
};
