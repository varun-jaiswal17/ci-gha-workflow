"""
Priority dispatcher: scores all applicable jobs for a PR event and fires
workflow_dispatch calls in score order (highest first).

Ships in shadow mode by default — set scheduler_mode: "live" in config.yaml
to actually reorder jobs.  In shadow mode, scores are logged but no dispatch
calls are made, so existing FIFO behavior is completely unchanged.

NOTE: workflow_dispatch requires a token with 'workflow' scope.
      GITHUB_TOKEN in Actions does not have this scope — you need a PAT or
      GitHub App token stored as a repository secret (e.g. CI_INTEL_PAT).
"""
from ci_intel.scheduler.score import compute_score


def get_applicable_jobs(pr_event, config):
    """Build a job_config list from the monitored_workflows in config."""
    workflows = config.get("monitored_workflows", [])
    return [
        {
            "workflow": wf,
            "workflow_id": wf,
            "name": wf,
            "branch": pr_event.get("head_ref", ""),
            "pr_number": pr_event.get("number"),
        }
        for wf in workflows
    ]


def dispatch_for_pr(pr_event, history, config, gh_client):
    """
    Score and (optionally) dispatch all applicable jobs for a PR event.

    pr_event: dict with at least {number, head_ref}
    history:  NdjsonStore instance
    config:   parsed config.yaml dict
    gh_client: GitHubClient instance (needs workflow_dispatch method)
    """
    weights = config.get("weights", {})
    shadow = config.get("scheduler_mode", "shadow") != "live"

    jobs = get_applicable_jobs(pr_event, config)
    scored = sorted(
        ((compute_score(j, history, weights), j) for j in jobs),
        key=lambda x: x[0],
        reverse=True,
    )

    for score, job in scored:
        if shadow:
            print(f"[dispatcher] shadow: would dispatch {job['name']!r} (score={score:.2f})")
        else:
            gh_client.workflow_dispatch(
                workflow_id=job["workflow_id"],
                ref=pr_event["head_ref"],
                inputs={"pr": str(pr_event["number"])},
            )
            print(f"[dispatcher] dispatched {job['name']!r} (score={score:.2f})")
