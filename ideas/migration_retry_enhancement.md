# Migration Retry & Failure Visibility Enhancement

## Concept
Extend the migration simulator to record per-patient stage failures and support optional retry logic so that simulated outages can be triaged or reprocessed interactively.

## Motivation
- Current simulator aggregates failures but doesn’t indicate which patient/stage failed.
- Real migration rehearsals benefit from knowing which records encountered issues and whether a retry resolves them.
- Enables practicing retry/backoff strategies, triage dashboards, and manual remediation flows.

## Key Features
1. **Failure Recording**
   - Capture patient ID, stage/substage, and simulated failure type (network timeout, system unavailable, etc.).
   - Persist failures to a structured output (CSV/JSON) and expose in migration analytics.

2. **Retry Mechanics**
   - Add optional `--retry-failures` flag with configurable max attempts/backoff.
   - When enabled, re-run failed patients through remaining stages, updating success/failure metrics accordingly.

3. **Reporting Updates**
   - Summaries of retries performed, remaining failures, and whether retries improved overall success.
   - Optionally generate a “triage list” for manual review.

## Considerations
- Retain deterministic behavior by logging the random seed and failure triggers.
- Ensure retries don’t skew quality scores unfairly; track original vs. retried outcomes.
- Decide how to represent failures that persist after retries (e.g., flag as hard fail).

## Next Steps
1. Design failure log schema and integrate with `BatchMigrationStatus`.
2. Implement retry loop with configurable strategy (immediate, backoff, manual confirmation).
3. Update migration analytics/reporting to surface retry statistics.
4. Create tests/demos showing improved success rate when transient issues are retried.
