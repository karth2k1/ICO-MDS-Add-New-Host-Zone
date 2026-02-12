# Customer Beta Release Checklist

This checklist is used before each customer-beta drop of the ICO Workflow Generator.

## 1) Functional Validation

- [ ] Rule-based generation (`/generate`) returns valid workflow JSON for baseline templates.
- [ ] LLM generation (`/generate/llm`) succeeds for representative MDS and generic WebApi scenarios.
- [ ] Context upload endpoint (`/context/upload`) accepts valid ICO JSON and rejects invalid payloads.
- [ ] GitHub public import (`/context/github/public`) imports ICO-compatible artifacts from a sample repo.
- [ ] Context provenance is included in LLM generation responses.

## 2) Quality And Regression

- [ ] `pytest` suite passes locally.
- [ ] CI workflow is green on the release branch.
- [ ] Regression fixture validation passes for known good workflow exports.
- [ ] No new critical validator errors compared to previous beta.

## 3) Security And Data Handling

- [ ] No credentials, tokens, or secrets are committed in code or docs.
- [ ] Uploaded artifact retention policy is communicated and enforced.
- [ ] Request limits are configured for context ingestion routes.
- [ ] Context metadata captures source provenance for every artifact.

## 4) Documentation And Operations

- [ ] `DESIGN_DOCUMENT.md` reflects current architecture and connector support.
- [ ] Release notes summarize changes, known limitations, and rollback plan.
- [ ] Support runbook includes common ingestion and generation failure modes.
- [ ] Demo script is updated for customer walkthrough.

## 5) Manual Intersight Certification

- [ ] At least one generated workflow is imported successfully in the beta tenant.
- [ ] Failure scenarios are validated with actionable error messaging.
- [ ] Import/export compatibility is verified for latest Intersight version.

