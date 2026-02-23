# Phase 1 Stability Baseline

Use this file to track the Phase 1 reliability gate.

## Targets

- Pass rate >= 95% over 20 consecutive CI runs
- Flaky retries <= 2%
- Smoke suite runtime <= 10 minutes

## Run Log

| Window | Total Runs | Pass Rate | Flaky Rate | Median Runtime (min) | Notes |
|---|---:|---:|---:|---:|---|
| Initial baseline | 0 | 0% | 0% | 0 | Populate from CI artifacts |

## How to gather metrics

1. Download `e2e/reports/junit/results.xml` artifacts from CI.
2. Run:
   - `python3 e2e/scripts/stability_report.py --input e2e/reports/junit/results.xml`
3. Update the table above each week.
