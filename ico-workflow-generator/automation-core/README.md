# Automation Core (Phase 2 Seed)

This folder is the initial extraction point for reusable Playwright helpers.

## Current shared modules

- `src/ui/openapiFilters.js`: normalize shared OpenAPI test options

## Extraction policy

- Keep only cross-project helpers here.
- Keep app-specific selectors and domain assertions in each app repo.
- Promote modules into a dedicated shared repo once at least two app repos use them.
