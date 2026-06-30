"""
Tests for ci_intel/collector/backfill.py using a fake GitHub client and
a local bare git repo as the store remote — no network access needed.

Run with:  pytest tests/test_backfill.py -v
"""
import io
import json
import subprocess
import tempfile
import zipfile
from pathlib import Path

import pytest

from ci_intel.collector.backfill import process_run, backfill_workflow
from ci_intel.store.ndjson_store import NdjsonStore


# ---------------------------------------------------------------------------
# Fake GitHub client
# ---------------------------------------------------------------------------

def _make_log_zip(*log_lines, flat=True):
    """
    Return a ZipFile for 'Test ARM64'.
    flat=True  → GitHub's real format: flat root file "1_Test ARM64.txt"
    flat=False → folder format: "Test ARM64/1_Run tests.txt"
    """
    buf = io.BytesIO()
    content = "\n".join(log_lines)
    with zipfile.ZipFile(buf, "w") as zf:
        if flat:
            zf.writestr("1_Test ARM64.txt", content)
        else:
            zf.writestr("Test ARM64/1_Run tests.txt", content)
    buf.seek(0)
    return zipfile.ZipFile(buf)


class FakeGitHubClient:
    """Minimal stub that covers the calls made by backfill.py."""

    def __init__(self, runs, jobs_by_run_id, logs_by_run_id=None):
        self._runs = runs                        # list of run dicts
        self._jobs = jobs_by_run_id              # {run_id: [job, ...]}
        self._logs = logs_by_run_id or {}        # {run_id: ZipFile}

    def list_workflows(self):
        return [{"id": 1, "name": "OCV PR:5.x ARM64"}]

    def find_workflow_id(self, name):
        for wf in self.list_workflows():
            if wf["name"] == name:
                return wf["id"]
        return None

    def list_workflow_runs(self, workflow_id, days=90, status="completed"):
        yield from self._runs

    def list_jobs(self, run_id):
        return self._jobs.get(run_id, [])

    def get_logs_zip(self, run_id):
        if run_id not in self._logs:
            raise RuntimeError(f"no logs for run {run_id}")
        return self._logs[run_id]


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def remote(tmp_path):
    bare = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--bare", str(bare)],
                   check=True, capture_output=True)
    return f"file://{bare}"


def make_store(remote_url):
    return NdjsonStore("test/repo", "fake", remote_url=remote_url)


FAILURE_RUN = {
    "id": 1001,
    "name": "OCV PR:5.x ARM64",
    "head_branch": "fix/core",
    "conclusion": "failure",
    "event": "pull_request",
    "pull_requests": [{"number": 42}],
    "run_started_at": "2026-06-30T10:00:00Z",
    "updated_at": "2026-06-30T10:05:00Z",
}

SUCCESS_RUN = {
    "id": 1002,
    "name": "OCV PR:5.x ARM64",
    "head_branch": "fix/core",
    "conclusion": "success",
    "event": "pull_request",
    "pull_requests": [{"number": 42}],
    "run_started_at": "2026-06-30T11:00:00Z",
    "updated_at": "2026-06-30T11:04:00Z",
}

FAILING_JOB = {
    "id": 9001,
    "name": "Test ARM64",
    "conclusion": "failure",
    "started_at": "2026-06-30T10:01:00Z",
    "completed_at": "2026-06-30T10:05:00Z",
    "steps": [{"name": "Run tests", "conclusion": "failure"}],
}

SUCCESS_JOB = {
    "id": 9002,
    "name": "Test ARM64",
    "conclusion": "success",
    "started_at": "2026-06-30T11:00:00Z",
    "completed_at": "2026-06-30T11:04:00Z",
    "steps": [],
}


# ---------------------------------------------------------------------------
# process_run unit tests
# ---------------------------------------------------------------------------

class TestProcessRun:
    def test_failure_run_classified(self):
        gh = FakeGitHubClient(
            runs=[FAILURE_RUN],
            jobs_by_run_id={1001: [FAILING_JOB]},
            logs_by_run_id={1001: _make_log_zip("[  FAILED  ] Core.test1 (5 ms)")},
        )
        fact = process_run(gh, FAILURE_RUN)
        assert fact["run_id"] == 1001
        assert fact["conclusion"] == "failure"
        assert fact["category"] == "TEST"
        assert fact["pr_number"] == 42
        assert fact["branch"] == "fix/core"
        assert fact["backfilled"] is True

    def test_success_run_stored_with_none_category(self):
        gh = FakeGitHubClient(
            runs=[SUCCESS_RUN],
            jobs_by_run_id={1002: [SUCCESS_JOB]},
        )
        fact = process_run(gh, SUCCESS_RUN)
        assert fact["run_id"] == 1002
        assert fact["conclusion"] == "success"
        assert fact["category"] is None
        assert fact["error_signature"] is None

    def test_infra_failure_classified(self):
        gh = FakeGitHubClient(
            runs=[FAILURE_RUN],
            jobs_by_run_id={1001: [FAILING_JOB]},
            logs_by_run_id={1001: _make_log_zip("out of memory", "Killed")},
        )
        fact = process_run(gh, FAILURE_RUN)
        assert fact["category"] == "INFRA"

    def test_build_failure_classified(self):
        gh = FakeGitHubClient(
            runs=[FAILURE_RUN],
            jobs_by_run_id={1001: [FAILING_JOB]},
            logs_by_run_id={1001: _make_log_zip("error: unknown type name 'cv::Mat'")},
        )
        fact = process_run(gh, FAILURE_RUN)
        assert fact["category"] == "BUILD"

    def test_flat_root_log_format_is_read(self):
        """GitHub ZIPs use '1_JobName.txt' flat files — must be read correctly."""
        gh = FakeGitHubClient(
            runs=[FAILURE_RUN],
            jobs_by_run_id={1001: [FAILING_JOB]},
            logs_by_run_id={1001: _make_log_zip("error: undefined reference", flat=True)},
        )
        fact = process_run(gh, FAILURE_RUN)
        assert fact["category"] == "BUILD"   # not UNKNOWN

    def test_folder_log_format_fallback(self):
        """Folder format 'Test ARM64/1_step.txt' still works as fallback."""
        gh = FakeGitHubClient(
            runs=[FAILURE_RUN],
            jobs_by_run_id={1001: [FAILING_JOB]},
            logs_by_run_id={1001: _make_log_zip("out of memory", flat=False)},
        )
        fact = process_run(gh, FAILURE_RUN)
        assert fact["category"] == "INFRA"

    def test_worst_category_wins_when_multiple_jobs_fail(self):
        """Run with both a BUILD job and a TEST job → reports BUILD (higher priority)."""
        build_job = {**FAILING_JOB, "id": 9010, "name": "Build"}
        test_job = {**FAILING_JOB, "id": 9011, "name": "Test ARM64"}

        def get_logs_zip(run_id):
            # Return different logs per call based on which job
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w") as zf:
                zf.writestr("Build/1_build.txt", "error: unknown type name 'cv::Mat'")
                zf.writestr("Test ARM64/1_Run tests.txt", "[  FAILED  ] Core.test1 (1 ms)")
            buf.seek(0)
            return zipfile.ZipFile(buf)

        gh = FakeGitHubClient(
            runs=[FAILURE_RUN],
            jobs_by_run_id={1001: [build_job, test_job]},
            logs_by_run_id={1001: get_logs_zip(1001)},
        )
        fact = process_run(gh, FAILURE_RUN)
        assert fact["category"] == "BUILD"

    def test_expired_logs_stores_fact_without_category(self):
        """If log download fails (expired), we still store the run-level fact."""
        gh = FakeGitHubClient(
            runs=[FAILURE_RUN],
            jobs_by_run_id={1001: [FAILING_JOB]},
            logs_by_run_id={},  # no logs → will raise → no verdicts → category=None
        )
        fact = process_run(gh, FAILURE_RUN)
        assert fact is not None
        assert fact["run_id"] == 1001
        assert fact["conclusion"] == "failure"
        assert fact["category"] is None

    def test_cancelled_run_skips_classification(self):
        """Cancelled runs are not real failures — stored as CANCELLED without job processing."""
        cancelled_run = {
            **FAILURE_RUN,
            "id": 1005,
            "conclusion": "cancelled",
        }
        gh = FakeGitHubClient(
            runs=[cancelled_run],
            jobs_by_run_id={},   # should never be called
            logs_by_run_id={},
        )
        fact = process_run(gh, cancelled_run)
        assert fact["conclusion"] == "cancelled"
        assert fact["category"] == "CANCELLED"
        assert fact["error_signature"] is None

    def test_duration_computed(self):
        gh = FakeGitHubClient(
            runs=[SUCCESS_RUN],
            jobs_by_run_id={1002: [SUCCESS_JOB]},
        )
        fact = process_run(gh, SUCCESS_RUN)
        assert fact["duration_sec"] == 4 * 60  # 11:00 to 11:04

    def test_push_event_has_no_pr_number(self):
        push_run = {**FAILURE_RUN, "event": "push", "pull_requests": []}
        gh = FakeGitHubClient(
            runs=[push_run],
            jobs_by_run_id={1001: [FAILING_JOB]},
            logs_by_run_id={1001: _make_log_zip("error: something")},
        )
        fact = process_run(gh, push_run)
        assert fact["pr_number"] is None


# ---------------------------------------------------------------------------
# backfill_workflow integration tests
# ---------------------------------------------------------------------------

class TestBackfillWorkflow:
    def test_writes_facts_to_store(self, remote):
        gh = FakeGitHubClient(
            runs=[FAILURE_RUN, SUCCESS_RUN],
            jobs_by_run_id={
                1001: [FAILING_JOB],
                1002: [SUCCESS_JOB],
            },
            logs_by_run_id={1001: _make_log_zip("[  FAILED  ] Core.test1 (5 ms)")},
        )
        store = make_store(remote)
        seen, written = backfill_workflow(
            gh, store, "OCV PR:5.x ARM64", days=90, dry_run=False, skip_ids=set()
        )
        assert seen == 2
        assert written == 2

        # Verify the store received both facts
        with tempfile.TemporaryDirectory() as d:
            subprocess.run(
                ["git", "clone", "--branch", "ci-intel-data", remote, d],
                check=True, capture_output=True,
            )
            rows = [
                json.loads(l)
                for l in (Path(d) / "data" / "runs.ndjson").read_text().splitlines()
                if l.strip()
            ]
        assert {r["run_id"] for r in rows} == {1001, 1002}
        failure = next(r for r in rows if r["run_id"] == 1001)
        success = next(r for r in rows if r["run_id"] == 1002)
        assert failure["category"] == "TEST"
        assert success["category"] is None

    def test_skips_already_stored_runs(self, remote):
        gh = FakeGitHubClient(
            runs=[FAILURE_RUN, SUCCESS_RUN],
            jobs_by_run_id={1001: [FAILING_JOB], 1002: [SUCCESS_JOB]},
            logs_by_run_id={1001: _make_log_zip("error: something")},
        )
        store = make_store(remote)
        # Pre-populate skip_ids with run 1001
        seen, written = backfill_workflow(
            gh, store, "OCV PR:5.x ARM64", days=90, dry_run=False, skip_ids={1001}
        )
        assert seen == 2
        assert written == 1  # only 1002 was new

    def test_dry_run_does_not_write(self, remote):
        gh = FakeGitHubClient(
            runs=[FAILURE_RUN],
            jobs_by_run_id={1001: [FAILING_JOB]},
            logs_by_run_id={1001: _make_log_zip("error: something")},
        )
        store = make_store(remote)
        _, written = backfill_workflow(
            gh, store, "OCV PR:5.x ARM64", days=90, dry_run=True, skip_ids=set()
        )
        assert written == 0
        assert store.existing_run_ids() == set()

    def test_unknown_workflow_returns_zero(self, remote):
        gh = FakeGitHubClient(runs=[], jobs_by_run_id={})
        store = make_store(remote)
        seen, written = backfill_workflow(
            gh, store, "NonExistent Workflow", days=90, dry_run=False, skip_ids=set()
        )
        assert seen == 0
        assert written == 0


# ---------------------------------------------------------------------------
# End-to-end: store queries work correctly after backfill
# ---------------------------------------------------------------------------

class TestQueriesAfterBackfill:
    def test_failed_on_prev_run_detected(self, remote):
        gh = FakeGitHubClient(
            runs=[FAILURE_RUN],
            jobs_by_run_id={1001: [FAILING_JOB]},
            logs_by_run_id={1001: _make_log_zip("[  FAILED  ] Core.test1 (5 ms)")},
        )
        store = make_store(remote)
        backfill_workflow(gh, store, "OCV PR:5.x ARM64", 90, False, set())
        result = store.last_run_for_pr(42, "OCV PR:5.x ARM64")
        assert result is not None
        assert result["conclusion"] == "failure"

    def test_flake_detected_after_backfill(self, remote):
        # PR 42: run 1001 fails, run 1002 succeeds → flake
        gh = FakeGitHubClient(
            runs=[FAILURE_RUN, SUCCESS_RUN],
            jobs_by_run_id={1001: [FAILING_JOB], 1002: [SUCCESS_JOB]},
            logs_by_run_id={1001: _make_log_zip("[  FAILED  ] Core.test1 (1 ms)")},
        )
        store = make_store(remote)
        backfill_workflow(gh, store, "OCV PR:5.x ARM64", 90, False, set())
        assert store.flake_count("OCV PR:5.x ARM64") == 1

    def test_median_duration_after_backfill(self, remote):
        gh = FakeGitHubClient(
            runs=[FAILURE_RUN],
            jobs_by_run_id={1001: [FAILING_JOB]},
            logs_by_run_id={1001: _make_log_zip("error: something")},
        )
        store = make_store(remote)
        backfill_workflow(gh, store, "OCV PR:5.x ARM64", 90, False, set())
        dur = store.median_duration("OCV PR:5.x ARM64")
        assert dur == 5 * 60  # 10:00 to 10:05

    def test_branch_stability_uses_success_runs(self, remote):
        # One failure + one success → 50% failure rate, stability is meaningful
        gh = FakeGitHubClient(
            runs=[FAILURE_RUN, SUCCESS_RUN],
            jobs_by_run_id={1001: [FAILING_JOB], 1002: [SUCCESS_JOB]},
            logs_by_run_id={1001: _make_log_zip("error: something")},
        )
        store = make_store(remote)
        backfill_workflow(gh, store, "OCV PR:5.x ARM64", 90, False, set())
        runs = store.recent_runs("fix/core")
        assert len(runs) == 2
        fail_rate = sum(1 for r in runs if r["conclusion"] != "success") / len(runs)
        assert fail_rate == 0.5
