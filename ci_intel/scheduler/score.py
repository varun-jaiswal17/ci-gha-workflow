"""
Priority scoring function for CI job dispatch ordering.

Higher score = runs sooner.  Four weighted factors:
  1. failed_on_prev_run  — dominant; boost jobs the contributor is actively fixing
  2. flake_penalty       — penalize known time-wasters
  3. short_job_first     — faster feedback from shorter jobs
  4. branch_stability    — tiebreaker; stable branches get slight preference
"""


def compute_score(job_config, history, weights):
    """
    Return a numeric priority score for one job.

    job_config keys: branch, workflow, pr_number
    history: NdjsonStore instance (or any object with the same query API)
    weights: dict from config.yaml  (keys: failed_on_prev_run, flake_penalty,
                                           short_job_first, branch_stability)
    """
    branch = job_config["branch"]
    workflow = job_config["workflow"]
    pr_number = job_config["pr_number"]

    # Factor 1: did this job fail on the last run of this PR? (binary 0/1)
    last_run = history.last_run_for_pr(pr_number, workflow)
    failed_prev = 1 if last_run and last_run["conclusion"] == "failure" else 0

    # Factor 2: flake penalty — more flakes → lower score
    flakes = history.flake_count(workflow, lookback_days=30)
    flake_score = 1 / max(flakes, 1)

    # Factor 3: shortest-job-first — shorter median duration → higher score
    median_dur = history.median_duration(workflow) or 600
    duration_score = 1 / median_dur

    # Factor 4: branch stability — higher pass rate → higher score (tiebreaker)
    runs = history.recent_runs(branch, limit=50)
    fail_count = sum(1 for r in runs if r["conclusion"] != "success")
    fail_rate = fail_count / max(len(runs), 1)
    stability = 1 / max(fail_rate, 0.01)

    return (
        weights.get("failed_on_prev_run", 10.0) * failed_prev
        + weights.get("flake_penalty", 2.0) * flake_score
        + weights.get("short_job_first", 1.0) * duration_score
        + weights.get("branch_stability", 1.0) * stability
    )
