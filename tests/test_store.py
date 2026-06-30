"""
Tests for ci_intel/store/ndjson_store.py using a local bare git repo as the "remote".
No network access, no GitHub token needed.
Run with:  pytest tests/test_store.py -v
"""
import json
import subprocess
import tempfile
from pathlib import Path

import pytest

from ci_intel.store.ndjson_store import NdjsonStore


@pytest.fixture()
def remote(tmp_path):
    """Create a local bare git repo — stands in for the GitHub remote."""
    bare = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--bare", str(bare)],
                   check=True, capture_output=True)
    return f"file://{bare}"


def make_store(remote_url):
    return NdjsonStore("test/repo", "fake-token", remote_url=remote_url)


def read_ndjson(remote_url):
    """Clone the data branch and return all parsed rows."""
    with tempfile.TemporaryDirectory() as d:
        r = subprocess.run(
            ["git", "clone", "--branch", "ci-intel-data", remote_url, d],
            capture_output=True,
        )
        if r.returncode != 0:
            return []
        data_file = Path(d) / "data" / "runs.ndjson"
        if not data_file.exists():
            return []
        return [json.loads(l) for l in data_file.read_text().splitlines() if l.strip()]


BASE_FACT = {
    "run_id": 1001,
    "job_id": 9001,
    "job_name": "Test ARM64",
    "pr_number": 42,
    "branch": "fix/imgproc",
    "workflow": "OCV PR:5.x ARM64",
    "conclusion": "failure",
    "category": "TEST",
    "error_signature": "abc123def456",
    "module": "imgproc",
    "failing_tests": ["opencv_test_imgproc"],
    "duration_sec": 300,
    "created_at": "2026-06-30T12:00:00Z",
}


class TestUpsert:
    def test_creates_branch_on_first_write(self, remote):
        make_store(remote).upsert_fact(BASE_FACT)
        rows = read_ndjson(remote)
        assert len(rows) == 1
        assert rows[0]["run_id"] == 1001

    def test_appends_second_fact(self, remote):
        store = make_store(remote)
        store.upsert_fact(BASE_FACT)
        store._cache = None  # force fresh clone on next write
        store.upsert_fact({**BASE_FACT, "run_id": 1002, "pr_number": 43})
        rows = read_ndjson(remote)
        assert len(rows) == 2
        assert {r["run_id"] for r in rows} == {1001, 1002}

    def test_each_row_is_valid_json(self, remote):
        make_store(remote).upsert_fact(BASE_FACT)
        with tempfile.TemporaryDirectory() as d:
            subprocess.run(
                ["git", "clone", "--branch", "ci-intel-data", remote, d],
                check=True, capture_output=True,
            )
            raw = (Path(d) / "data" / "runs.ndjson").read_text()
        for line in raw.splitlines():
            json.loads(line)  # raises if invalid


class TestQueryMethods:
    def test_last_run_for_pr_found(self, remote):
        store = make_store(remote)
        store.upsert_fact(BASE_FACT)
        result = store.last_run_for_pr(42, "OCV PR:5.x ARM64")
        assert result is not None
        assert result["run_id"] == 1001

    def test_last_run_for_pr_wrong_workflow(self, remote):
        store = make_store(remote)
        store.upsert_fact(BASE_FACT)
        result = store.last_run_for_pr(42, "OCV PR:4.x ARM64")
        assert result is None

    def test_last_run_for_pr_wrong_pr(self, remote):
        store = make_store(remote)
        store.upsert_fact(BASE_FACT)
        assert store.last_run_for_pr(99, "OCV PR:5.x ARM64") is None

    def test_last_run_returns_highest_run_id(self, remote):
        store = make_store(remote)
        store.upsert_fact(BASE_FACT)
        store._cache = None
        store.upsert_fact({**BASE_FACT, "run_id": 1002})
        result = store.last_run_for_pr(42, "OCV PR:5.x ARM64")
        assert result["run_id"] == 1002

    def test_median_duration(self, remote):
        store = make_store(remote)
        store.upsert_fact(BASE_FACT)
        assert store.median_duration("OCV PR:5.x ARM64") == 300.0

    def test_median_duration_unknown_workflow(self, remote):
        store = make_store(remote)
        store.upsert_fact(BASE_FACT)
        assert store.median_duration("OCV PR:4.x ARM64") is None

    def test_recent_runs_returns_match(self, remote):
        store = make_store(remote)
        store.upsert_fact(BASE_FACT)
        runs = store.recent_runs("fix/imgproc")
        assert len(runs) == 1
        assert runs[0]["run_id"] == 1001

    def test_recent_runs_wrong_branch(self, remote):
        store = make_store(remote)
        store.upsert_fact(BASE_FACT)
        assert store.recent_runs("main") == []

    def test_recent_runs_limit(self, remote):
        store = make_store(remote)
        store.upsert_fact(BASE_FACT)
        store._cache = None
        store.upsert_fact({**BASE_FACT, "run_id": 1002})
        runs = store.recent_runs("fix/imgproc", limit=1)
        assert len(runs) == 1
        assert runs[0]["run_id"] == 1002  # newest first

    def test_flake_count_retry_pattern(self, remote):
        # PR 42: run 1001 fails with sig X, run 1002 succeeds → flake detected
        store = make_store(remote)
        store.upsert_fact(BASE_FACT)   # run 1001, pr=42, failure, sig=abc123def456
        store._cache = None
        store.upsert_fact({**BASE_FACT, "run_id": 1002, "conclusion": "success",
                           "error_signature": None, "category": None})
        assert store.flake_count("OCV PR:5.x ARM64") == 1

    def test_flake_count_only_failures_is_zero(self, remote):
        # Same PR, two consecutive failures → consistent failure, not a flake
        store = make_store(remote)
        store.upsert_fact(BASE_FACT)
        store._cache = None
        store.upsert_fact({**BASE_FACT, "run_id": 1002})
        assert store.flake_count("OCV PR:5.x ARM64") == 0

    def test_existing_run_ids(self, remote):
        store = make_store(remote)
        store.upsert_fact(BASE_FACT)
        ids = store.existing_run_ids()
        assert 1001 in ids


class TestEmptyStore:
    def test_queries_on_empty_store_return_safe_defaults(self, remote):
        # Don't write anything — queries must not raise
        store = make_store(remote)
        store.upsert_fact(BASE_FACT)

        other = make_store(remote)  # fresh store, will load from branch
        assert other.last_run_for_pr(0, "nonexistent") is None
        assert other.median_duration("nonexistent") is None
        assert other.recent_runs("nonexistent") == []
        assert other.flake_count("nonexistent") == 0
