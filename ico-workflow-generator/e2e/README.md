# E2E (Playwright)

## Local commands

- Install browser:
  - `npm run e2e:install`
- Run smoke suite:
  - `npm run e2e:smoke`
- Run all e2e:
  - `npm run e2e`
- Run headed:
  - `npm run e2e:headed`

## Artifacts

Playwright reports are generated under:

- `e2e/reports/html`
- `e2e/reports/junit/results.xml`

## Stability tracking

Use the helper script to summarize JUnit history exported from CI:

```bash
python3 e2e/scripts/stability_report.py --input e2e/reports/junit/results.xml
```

Target thresholds (Phase 1 exit):

- Pass rate >= 95%
- Flaky retries <= 2%
- Smoke runtime <= 10 minutes
