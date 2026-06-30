# CI-Intel

Intelligent monitoring and priority scheduling for the OpenCV GitHub Actions CI pipeline.

## What it does

**Phase 1 (this branch)** — Observe and classify

After every monitored PR workflow completes, the `OCV-CI-Intel-Ingest` workflow:
1. Downloads the run's log ZIP and structured results artifact.
2. Classifies each failing job as `INFRA`, `CONFIG`, `TEST`, `BUILD`, or `UNKNOWN`.
3. Appends one NDJSON fact row per failed job to the `ci-intel-data` branch.

**Phase 3** — Priority dispatch *(shadow mode, no reordering yet)*

The scheduler scores each job using four factors (see `scheduler/score.py`) and logs
what order it *would* dispatch them in. Live reordering requires flipping
`scheduler_mode: live` in `config.yaml` and providing a `CI_INTEL_PAT` secret.

## Repository structure

```
ci_intel/
  collector/
    github_client.py    — GitHub REST API wrapper
    ingest.py           — entry point; orchestrates fetch → classify → store
  classifier/
    rules.py            — ordered rule cascade (INFRA > CONFIG > TEST > BUILD)
    classify.py         — walks rules, returns structured fact dict
    signatures.py       — normalizes log lines into stable 12-char SHA-1 hashes
  store/
    ndjson_store.py     — append-only NDJSON store on the ci-intel-data branch
  scheduler/
    score.py            — weighted priority score per job
    dispatcher.py       — fires workflow_dispatch calls in score order
  config.example.yaml   — tunable settings (copy to config.yaml to deploy)
  requirements.txt      — pinned Python dependencies

.github/workflows/
  OCV-CI-Intel-Ingest.yaml  — the one new workflow; fires on workflow_run completed
```

## Deployment

### Prerequisites

- This file (`OCV-CI-Intel-Ingest.yaml`) **must be merged to the default branch**
  before `workflow_run` triggers will fire.
- The workflow uses `GITHUB_TOKEN` (automatically available) for reads and for
  pushing to the `ci-intel-data` branch (`contents: write` permission is set).

### Steps

1. Merge this branch to `main`.
2. Copy `ci_intel/config.example.yaml` → `ci_intel/config.yaml` and adjust
   `monitored_workflows` to match your repo's workflow names exactly.
3. The `ci-intel-data` branch is created automatically on the first ingest run.

### Live scheduling (Phase 3)

1. Create a GitHub PAT with `workflow` scope and store it as secret `CI_INTEL_PAT`.
2. Set `scheduler_mode: live` in `config.yaml`.
3. The existing PR workflows must expose a `workflow_dispatch` trigger (see the
   dispatcher module for details on the trigger-change requirement).

## Data format

Each row in `data/runs.ndjson` on the `ci-intel-data` branch:

```json
{
  "run_id": 12345678,
  "job_id": 99887766,
  "job_name": "Test ARM64",
  "pr_number": 42,
  "branch": "fix/imgproc-crash",
  "workflow": "OCV PR:5.x ARM64",
  "conclusion": "failure",
  "category": "TEST",
  "error_signature": "a3f1b2c4d5e6",
  "module": "imgproc",
  "failing_tests": ["opencv_test_imgproc"],
  "duration_sec": 312,
  "created_at": "2026-06-30T14:22:01Z"
}
```

## Migrating to a real database

To swap the NDJSON store for PostgreSQL/Supabase:

1. Implement the same five methods (`upsert_fact`, `last_run_for_pr`, `flake_count`,
   `median_duration`, `recent_runs`) in a new `ci_intel/store/pg_store.py`.
2. Replace `NdjsonStore(...)` with `PgStore(...)` in `collector/ingest.py`.
3. Backfill historical data from the NDJSON file with a one-time script.

No other code changes are needed — the classifier and scheduler are store-agnostic.
