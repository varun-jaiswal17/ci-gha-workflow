"""
Priority gate — the runtime that turns a score into real job ordering.

Runs as a lightweight job at the front of a gated workflow (on a cheap
ubuntu-latest runner).  The expensive jobs declare `needs: priority-gate`, so
they do not grab a scarce self-hosted runner until this gate releases them.

Flow:
    enter   — score this (PR, workflow) from the store and enroll in the queue
    wait    — poll until fewer than MAX_CONCURRENT runs are active AND this run
              is the highest-scored waiter, then release (exit 0)
    release — called when the run finishes, freeing its slot for the next waiter

The gate is deadlock-safe: if it cannot get a slot within --timeout seconds it
fails open (releases anyway), so a stuck queue can never block CI indefinitely.

Two subcommands, both driven entirely by env + flags so the composite action
can call them with no glue code:

    python -m ci_intel.scheduler.gate enter   --run-id 123 --workflow "OCV PR:5.x ARM64" --pr 42
    python -m ci_intel.scheduler.gate release --run-id 123

Env vars:
    GITHUB_TOKEN          token with contents:write on the store repo
    CI_INTEL_REPO         repo whose ci-intel-data branch holds queue + history
                          (defaults to GITHUB_REPOSITORY, set by Actions)
"""
import argparse
import os
import sys
import time

from ci_intel.scheduler.score import compute_score
from ci_intel.store.ndjson_store import NdjsonStore
from ci_intel.scheduler.queue_store import QueueStore

# Defaults — overridable per workflow via the composite action inputs.
DEFAULT_MAX_CONCURRENT = 1     # active runs allowed at once (model the runner pool)
DEFAULT_TIMEOUT = 1800         # seconds before failing open (never deadlock CI)
DEFAULT_POLL_INTERVAL = 30     # seconds between queue checks
STALE_TTL = 900               # drop a queue entry whose heartbeat is this old

DEFAULT_WEIGHTS = {
    "failed_on_prev_run": 10.0,
    "flake_penalty": 2.0,
    "short_job_first": 1.0,
    "branch_stability": 1.0,
}


def _stores(now_fn=time.time):
    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("CI_INTEL_REPO") or os.environ.get("GITHUB_REPOSITORY")
    if not token or not repo:
        print("error: GITHUB_TOKEN and CI_INTEL_REPO (or GITHUB_REPOSITORY) must be set",
              file=sys.stderr)
        sys.exit(2)
    return NdjsonStore(repo, token), QueueStore(repo, token)


def cmd_enter(args, history, queue, now_fn=time.time, sleep_fn=time.sleep):
    """Score this run, enroll it, and block until released. Always exits 0."""
    group = getattr(args, "group", None) or None
    job = {"branch": args.branch or "", "workflow": args.workflow, "pr_number": args.pr}
    score = compute_score(job, history, DEFAULT_WEIGHTS)
    print(f"[gate] run {args.run_id} workflow={args.workflow!r} pr={args.pr} "
          f"pool={group or 'global'} score={score:.3f}")

    queue.enter(args.run_id, args.workflow, args.pr, score, now_fn(), group=group)

    start = now_fn()
    while True:
        if queue.try_claim(args.run_id, args.max_concurrent, STALE_TTL, now_fn(), group=group):
            waited = int(now_fn() - start)
            print(f"[gate] RELEASED run {args.run_id} after {waited}s (score={score:.3f})")
            return 0

        elapsed = now_fn() - start
        if elapsed >= args.timeout:
            print(f"[gate] TIMEOUT after {int(elapsed)}s — failing open, releasing run {args.run_id}")
            queue.force_claim(args.run_id, now_fn())
            return 0

        waiting = [e for e in queue.snapshot()
                   if e["state"] == "waiting" and e.get("group") == group]
        ahead = sum(1 for e in waiting if (-e["score"], e["run_id"]) < (-score, args.run_id))
        print(f"[gate] run {args.run_id} waiting in pool {group or 'global'} — "
              f"{ahead} higher-priority run(s) ahead; re-check in {args.poll_interval}s")
        sleep_fn(args.poll_interval)


def cmd_release(args, history, queue, **_):
    """Remove this run from the queue, freeing its slot. Always exits 0."""
    queue.release(args.run_id)
    print(f"[gate] released slot for run {args.run_id}")
    return 0


def build_parser():
    p = argparse.ArgumentParser(description="CI priority gate")
    sub = p.add_subparsers(dest="command", required=True)

    enter = sub.add_parser("enter", help="enroll and wait for release")
    enter.add_argument("--run-id", type=int, required=True)
    enter.add_argument("--workflow", required=True)
    enter.add_argument("--pr", type=int, default=None)
    enter.add_argument("--branch", default=None)
    enter.add_argument("--group", default=None,
                       help="Queue partition (use the runner-pool label). Omit for one global pool.")
    enter.add_argument("--max-concurrent", type=int, default=DEFAULT_MAX_CONCURRENT)
    enter.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    enter.add_argument("--poll-interval", type=int, default=DEFAULT_POLL_INTERVAL)
    enter.set_defaults(func=cmd_enter)

    release = sub.add_parser("release", help="free this run's slot")
    release.add_argument("--run-id", type=int, required=True)
    release.set_defaults(func=cmd_release)

    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    history, queue = _stores()
    return args.func(args, history, queue)


if __name__ == "__main__":
    sys.exit(main())
