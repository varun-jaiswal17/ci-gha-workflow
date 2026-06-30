"""
Entry point for the CI-Intel ingest workflow.

Given a completed workflow run ID, this script:
  1. Fetches run metadata (PR, branch, conclusion, timing).
  2. Lists all jobs; classifies each failing job.
  3. Picks the highest-severity category across all failing jobs.
  4. Stores ONE fact per run in the NDJSON store.

One fact per run (not per job) keeps the scoring queries correct:
  - branch_stability  — needs success runs in the store, not just failures
  - median_duration   — deduplicates naturally
  - failed_on_prev_run / flake_count — use run-level conclusion
"""
import argparse
import os
import sys
from datetime import datetime, timezone

from ci_intel.classifier.classify import classify, CATEGORY_PRIORITY
from ci_intel.collector.github_client import GitHubClient
from ci_intel.collector.logs import fetch_job_logs
from ci_intel.store.ndjson_store import NdjsonStore


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


def run(run_id):
    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("CI_INTEL_REPO")
    if not token or not repo:
        print("[ingest] error: GITHUB_TOKEN and CI_INTEL_REPO must be set", file=sys.stderr)
        sys.exit(1)

    gh = GitHubClient(repo, token)
    store = NdjsonStore(repo, token)

    run_data = gh.get_run(run_id)
    workflow_name = run_data.get("name", "")
    branch = run_data.get("head_branch", "")
    overall_conclusion = run_data.get("conclusion", "success")
    run_duration = _duration(run_data.get("run_started_at"), run_data.get("updated_at"))

    pr_number = None
    if run_data.get("event") == "pull_request":
        prs = run_data.get("pull_requests", [])
        if prs:
            pr_number = prs[0]["number"]

    completed_at = run_data.get("updated_at") or datetime.now(timezone.utc).isoformat()

    jobs = gh.list_jobs(run_id)
    verdicts = []  # one entry per failing job
    logs_zip = None

    for job in jobs:
        name = job.get("name", "")
        conclusion = job.get("conclusion") or "success"

        if conclusion == "success":
            print(f"[ingest] job={name!r} -> SUCCESS")
            continue

        if logs_zip is None:
            try:
                logs_zip = gh.get_logs_zip(run_id)
            except Exception as e:
                print(f"[ingest] warn: could not fetch logs: {e}")

        log_text = fetch_job_logs(logs_zip, job) if logs_zip else ""
        failing_step = next(
            (s["name"] for s in job.get("steps", []) if s.get("conclusion") == "failure"),
            None,
        )
        verdict = classify(conclusion, failing_step, log_text, results_json=None)
        verdicts.append(verdict)
        print(
            f"[ingest] job={name!r}"
            f" -> {verdict['category']}"
            f" sig={verdict.get('error_signature') or '-'}"
            f" module={verdict.get('module') or '-'}"
        )

    # Pick the highest-severity verdict for the run-level fact
    best = max(verdicts, key=lambda v: CATEGORY_PRIORITY.get(v["category"], -1)) \
           if verdicts else {}

    fact = {
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
    }
    store.upsert_fact(fact)
    print(f"[ingest] stored run {run_id} -> {fact['conclusion']} / {fact['category']}")


def main():
    parser = argparse.ArgumentParser(description="Ingest a completed GitHub Actions run")
    parser.add_argument("--run-id", type=int, required=True)
    run(parser.parse_args().run_id)


if __name__ == "__main__":
    main()
