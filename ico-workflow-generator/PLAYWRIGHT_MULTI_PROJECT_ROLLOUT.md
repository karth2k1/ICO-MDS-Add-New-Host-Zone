# Playwright Multi-Project Rollout (Phase 3)

## Test taxonomy

- Smoke tests: PR gate, fast and deterministic.
- Regression tests: nightly schedule.
- Exploratory suites: manual trigger.

## Ownership model

- App team owns selectors and app-specific assertions.
- Automation maintainer owns shared core helpers and CI templates.

## New project onboarding checklist

1. Copy e2e scaffold (`tests`, `fixtures`, `helpers`).
2. Add `playwright.config.js` with app-local `webServer`.
3. Add `npm` scripts (`e2e`, `e2e:smoke`, `e2e:headed`).
4. Add CI smoke job with Playwright artifact upload.
5. Add at least 3 smoke tests:
   - primary happy path
   - one validation error path
   - one navigation/mode behavior path
6. Add stability baseline file and start weekly updates.

## Reporting metrics

- Pass rate by project
- Flaky retry rate by project
- Median smoke runtime by project
- Top failing test names over trailing 30 days
