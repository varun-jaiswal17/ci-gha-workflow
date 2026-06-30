"""
Backfill historical CI run data into the NDJSON store.

Fetches the last N days of completed runs for each monitored workflow,
classifies failures using raw log text (no structured JSON artifact — that
only exists for runs after Phase 1 was merged), and writes one fact per run.

After backfilling 30-90 days, the priority dispatcher has real scoring data
and can be enabled immediately instead of waiting weeks for live data.

Usage:
    # Backfill last 90 days for all default monitored workflows
    python -m ci_intel.collector.backfill

    # One specific workflow, last 14 days
    python -m ci_intel.collector.backfill --days 14 --workflow "OCV PR:5.x ARM64"

    # See what would be fetched without writing anything
    python -m ci_intel.collector.backfill --days 7 --dry-run

Required env vars:
    GITHUB_TOKEN           — personal access token with actions:read scope
    CI_INTEL_REPO          — repo where the ci-intel-data STORE branch lives
                             (your fork: "varun-jaiswal17/ci-gha-workflow")
    CI_INTEL_SOURCE_REPO   — repo to READ run history from (optional)
                             defaults to CI_INTEL_REPO
                             set to "opencv/ci-gha-workflow" to read upstream data
"""
import argparse
import os
import sys
import time
from datetime import datetime, timezone

from ci_intel.classifier.classify import classify, CATEGORY_PRIORITY
from ci_intel.collector.github_client import GitHubClient
from ci_intel.collector.logs import fetch_job_logs
from ci_intel.store.ndjson_store import NdjsonStore

# Default workflows to backfill when --workflow is not specified.
# Edit this list to match the `name:` fields in your workflow YAML files.
DEFAULT_WORKFLOWS = [
    "OCV PR:5.x ARM64",
    "OCV PR:5.x W10",
    "OCV PR:5.x macOS ARM64",
    "OCV PR:5.x macOS x86_64",
    "OCV PR:4.x ARM64",
    "OCV PR:4.x W10",
]

# Seconds to sleep between API calls — keeps well under the 5000 req/hr limit
API_SLEEP = 0.3


def _parse_ts(ts_str):
    if not ts_str:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            dt = datetime.strptime(ts_str, fmt)
            return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
        except ValueError:
            continue
    return None


def _duration(started, completed):
    a, b = _parse_ts(started), _parse_ts(completed)
    return max(0, int((b - a).total_seconds())) if a and b else None


def process_run(gh, run_data, dry_run=False):
    """
    Classify all failing jobs in one run and return a single run-level fact dict.
    Returns None if logs are unavailable (expired or network error).
    """
    run_id = run_data["id"]
    workflow_name = run_data.get("name", "")
    branch = run_data.get("head_branch", "")
    overall_conclusion = run_data.get("conclusion", "success")
    run_duration = _duration(run_data.get("run_started_at"), run_data.get("updated_at"))
    completed_at = run_data.get("updated_at", "")

    pr_number = None
    if run_data.get("event") == "pull_request":
        prs = run_data.get("pull_requests", [])
        if prs:
            pr_number = prs[0]["number"]

    # Cancelled runs are not real failures — store them as-is and skip classification.
    if overall_conclusion == "cancelled":
        return {
            "run_id": run_id,
            "pr_number": pr_number,
            "branch": branch,
            "workflow": workflow_name,
            "conclusion": "cancelled",
            "category": "CANCELLED",
            "error_signature": None,
            "module": None,
            "failing_tests": [],
            "duration_sec": run_duration,
            "created_at": completed_at,
            "backfilled": True,
        }

    jobs = gh.list_jobs(run_id)
    time.sleep(API_SLEEP)

    failing_jobs = [j for j in jobs if (j.get("conclusion") or "success") != "success"]

    verdicts = []
    logs_zip = None

    for job in failing_jobs:
        name = job.get("name", "")
        conclusion = job.get("conclusion", "failure")

        if logs_zip is None:
            try:
                logs_zip = gh.get_logs_zip(run_id)
                time.sleep(API_SLEEP)
            except Exception as e:
                print(f"    warn: logs unavailable for run {run_id}: {e}")
                # Log expiry is expected for old runs — store without category detail
                break

        log_text = fetch_job_logs(logs_zip, job) if logs_zip else ""
        failing_step = next(
            (s["name"] for s in job.get("steps", []) if s.get("conclusion") == "failure"),
            None,
        )
        verdict = classify(conclusion, failing_step, log_text, results_json=None)
        verdicts.append(verdict)
        print(f"    job={name!r} -> {verdict['category']} sig={verdict.get('error_signature') or '-'}")

    best = max(verdicts, key=lambda v: CATEGORY_PRIORITY.get(v["category"], -1)) \
           if verdicts else {}

    return {
        "run_id": run_id,
        "pr_number": pr_number,
        "branch": branch,
        "workflow": workflow_name,
        "conclusion": overall_conclusion,
        "category": best.get("category"),
        "error_signature": best.get("error_signature"),
        "module": best.get("module"),
        "failing_tests": [t for v in verdicts for t in v.get("failing_tests", [])],
        "duration_sec": run_duration,
        "created_at": completed_at,
        "backfilled": True,
    }


def backfill_workflow(gh, store, workflow_name, days, dry_run, skip_ids):
    """
    Process all recent runs for one workflow.
    Returns (total_seen, total_written).
    """
    print(f"\n[backfill] workflow={workflow_name!r} days={days}")

    workflow_id = gh.find_workflow_id(workflow_name)
    if workflow_id is None:
        print(f"  warn: workflow not found in repo — check the name matches the YAML 'name:' field")
        return 0, 0

    total_seen = 0
    total_written = 0

    for run_data in gh.list_workflow_runs(workflow_id, days=days):
        total_seen += 1
        run_id = run_data["id"]
        conclusion = run_data.get("conclusion", "")
        pr_info = f"PR#{run_data['pull_requests'][0]['number']}" \
                  if run_data.get("pull_requests") else run_data.get("head_branch", "")

        if run_id in skip_ids:
            print(f"  run {run_id} ({pr_info}, {conclusion}) — already stored, skipping")
            continue

        print(f"  run {run_id} ({pr_info}, {conclusion})")

        fact = process_run(gh, run_data, dry_run=dry_run)
        if fact is None:
            continue

        if dry_run:
            print(f"    DRY RUN: would store -> {fact['conclusion']} / {fact['category']}")
        else:
            store.upsert_fact(fact)
            skip_ids.add(run_id)  # update local set so concurrent writes don't duplicate
            total_written += 1

        time.sleep(API_SLEEP)

    return total_seen, total_written


def main():
    parser = argparse.ArgumentParser(
        description="Backfill historical CI run data into the NDJSON store"
    )
    parser.add_argument(
        "--workflow", action="append", dest="workflows", metavar="NAME",
        help="Workflow display name to backfill (repeatable). Default: all configured workflows.",
    )
    parser.add_argument(
        "--days", type=int, default=90,
        help="How many days of history to fetch (default: 90, GitHub max: ~90 for logs)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Fetch and classify but do not write to the store",
    )
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN")
    store_repo = os.environ.get("CI_INTEL_REPO")
    source_repo = os.environ.get("CI_INTEL_SOURCE_REPO") or store_repo
    if not token or not store_repo:
        print("error: GITHUB_TOKEN and CI_INTEL_REPO must be set", file=sys.stderr)
        print("       set CI_INTEL_SOURCE_REPO to read from a different repo (e.g. upstream)", file=sys.stderr)
        sys.exit(1)

    print(f"[backfill] reading runs from : {source_repo}")
    print(f"[backfill] writing store to  : {store_repo}")

    gh = GitHubClient(source_repo, token)   # reads upstream run history
    store = NdjsonStore(store_repo, token)  # writes to your fork

    workflows = args.workflows or DEFAULT_WORKFLOWS

    # Load existing run IDs once — avoids one git clone per run-existence check
    print("[backfill] loading existing run IDs from store...")
    skip_ids = store.existing_run_ids()
    print(f"[backfill] {len(skip_ids)} runs already stored, will skip")

    grand_seen = 0
    grand_written = 0

    for wf_name in workflows:
        seen, written = backfill_workflow(
            gh, store, wf_name, args.days, args.dry_run, skip_ids
        )
        grand_seen += seen
        grand_written += written

    action = "Would write" if args.dry_run else "Wrote"
    print(f"\n[backfill] done — {action} {grand_written}/{grand_seen} runs across {len(workflows)} workflows")


if __name__ == "__main__":
    main()
