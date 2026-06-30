"""
Tests for the priority gate (queue_store + gate logic).
Uses a local bare git repo as the "remote" — no network, no GitHub token.
Run with:  pytest tests/test_gate.py -v
"""
import subprocess

import pytest

from ci_intel.scheduler.queue_store import QueueStore
from ci_intel.scheduler import gate


@pytest.fixture()
def remote(tmp_path):
    bare = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--bare", str(bare)], check=True, capture_output=True)
    return f"file://{bare}"


def make_queue(remote_url):
    return QueueStore("test/repo", "fake-token", remote_url=remote_url)


# ----------------------------------------------------------------------
# QueueStore: enrolment, ordering, slots, staleness, release
# ----------------------------------------------------------------------

class TestQueueStore:
    def test_enter_creates_branch_and_entry(self, remote):
        q = make_queue(remote)
        q.enter(1, "wf", 10, score=5.0, now=1000.0)
        snap = q.snapshot()
        assert len(snap) == 1
        assert snap[0]["run_id"] == 1 and snap[0]["state"] == "waiting"

    def test_enter_is_idempotent(self, remote):
        q = make_queue(remote)
        q.enter(1, "wf", 10, score=5.0, now=1000.0)
        q.enter(1, "wf", 10, score=5.0, now=1000.0)
        assert len(q.snapshot()) == 1

    def test_single_waiter_claims_immediately(self, remote):
        q = make_queue(remote)
        q.enter(1, "wf", 10, score=5.0, now=1000.0)
        assert q.try_claim(1, max_concurrent=1, stale_ttl=900, now=1000.0) is True
        assert q.snapshot()[0]["state"] == "running"

    def test_highest_score_wins(self, remote):
        q = make_queue(remote)
        q.enter(1, "wf", 10, score=3.0, now=1000.0)
        q.enter(2, "wf", 11, score=9.0, now=1000.0)
        # Low-score run must NOT claim while a higher-score run waits.
        assert q.try_claim(1, max_concurrent=1, stale_ttl=900, now=1000.0) is False
        # High-score run claims the only slot.
        assert q.try_claim(2, max_concurrent=1, stale_ttl=900, now=1000.0) is True

    def test_slot_limit_blocks_second_run(self, remote):
        q = make_queue(remote)
        q.enter(1, "wf", 10, score=9.0, now=1000.0)
        q.enter(2, "wf", 11, score=3.0, now=1000.0)
        assert q.try_claim(1, max_concurrent=1, stale_ttl=900, now=1000.0) is True
        # Slot is full — second run cannot claim even though it is next.
        assert q.try_claim(2, max_concurrent=1, stale_ttl=900, now=1000.0) is False

    def test_release_frees_slot_for_next(self, remote):
        q = make_queue(remote)
        q.enter(1, "wf", 10, score=9.0, now=1000.0)
        q.enter(2, "wf", 11, score=3.0, now=1000.0)
        q.try_claim(1, max_concurrent=1, stale_ttl=900, now=1000.0)
        q.release(1)
        assert q.try_claim(2, max_concurrent=1, stale_ttl=900, now=1000.0) is True

    def test_higher_concurrency_allows_two(self, remote):
        q = make_queue(remote)
        q.enter(1, "wf", 10, score=9.0, now=1000.0)
        q.enter(2, "wf", 11, score=3.0, now=1000.0)
        assert q.try_claim(1, max_concurrent=2, stale_ttl=900, now=1000.0) is True
        assert q.try_claim(2, max_concurrent=2, stale_ttl=900, now=1000.0) is True

    def test_fifo_tiebreak_on_equal_score(self, remote):
        q = make_queue(remote)
        q.enter(5, "wf", 10, score=4.0, now=1000.0)
        q.enter(3, "wf", 11, score=4.0, now=1000.0)
        # Equal score → lower run_id (earlier) goes first.
        assert q.try_claim(5, max_concurrent=1, stale_ttl=900, now=1000.0) is False
        assert q.try_claim(3, max_concurrent=1, stale_ttl=900, now=1000.0) is True

    def test_stale_running_entry_is_pruned(self, remote):
        q = make_queue(remote)
        q.enter(1, "wf", 10, score=9.0, now=1000.0)
        q.try_claim(1, max_concurrent=1, stale_ttl=900, now=1000.0)  # run 1 now "running"
        q.enter(2, "wf", 11, score=3.0, now=2000.0)
        # Run 1's heartbeat (1000) is now older than stale_ttl → pruned, slot freed.
        assert q.try_claim(2, max_concurrent=1, stale_ttl=900, now=2000.0) is True

    def test_force_claim_marks_running(self, remote):
        q = make_queue(remote)
        q.enter(1, "wf", 10, score=1.0, now=1000.0)
        q.enter(2, "wf", 11, score=9.0, now=1000.0)
        q.force_claim(1, now=1000.0)  # fail-open even though run 2 scores higher
        states = {e["run_id"]: e["state"] for e in q.snapshot()}
        assert states[1] == "running"


# ----------------------------------------------------------------------
# gate.cmd_enter / cmd_release with a fake clock (no real sleeping)
# ----------------------------------------------------------------------

class FakeHistory:
    """Minimal stand-in for NdjsonStore so compute_score returns a fixed value."""
    def last_run_for_pr(self, pr, wf):
        return {"conclusion": "failure"} if pr == 42 else None

    def flake_count(self, wf, lookback_days=30):
        return 0

    def median_duration(self, wf):
        return 600

    def recent_runs(self, branch, limit=50):
        return []


class Args:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def test_cmd_enter_releases_when_alone(remote):
    q = make_queue(remote)
    args = Args(run_id=1, workflow="wf", pr=42, branch="b",
                max_concurrent=1, timeout=300, poll_interval=5)
    rc = gate.cmd_enter(args, FakeHistory(), q, now_fn=lambda: 1000.0)
    assert rc == 0
    assert q.snapshot()[0]["state"] == "running"


def test_cmd_enter_fails_open_on_timeout(remote):
    q = make_queue(remote)
    # A higher-score run holds the only slot so run 2 can never claim normally.
    q.enter(1, "wf", 10, score=99.0, now=0.0)
    q.try_claim(1, max_concurrent=1, stale_ttl=10_000, now=0.0)

    clock = {"t": 0.0}
    def now():
        return clock["t"]
    def fake_sleep(s):
        clock["t"] += s

    args = Args(run_id=2, workflow="wf", pr=1, branch="b",
                max_concurrent=1, timeout=20, poll_interval=5)
    rc = gate.cmd_enter(args, FakeHistory(), q, now_fn=now, sleep_fn=fake_sleep)
    assert rc == 0
    states = {e["run_id"]: e["state"] for e in q.snapshot()}
    assert states[2] == "running"  # forced open after timeout


def test_cmd_release_removes_entry(remote):
    q = make_queue(remote)
    q.enter(1, "wf", 10, score=5.0, now=1000.0)
    rc = gate.cmd_release(Args(run_id=1), FakeHistory(), q)
    assert rc == 0
    assert q.snapshot() == []
