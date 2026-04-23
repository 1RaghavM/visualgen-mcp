"""Tests for the in-memory job store."""

from __future__ import annotations

import threading

from visualgen_mcp.jobs import JobStatus, JobStore


def test_create_returns_pending_job() -> None:
    store = JobStore()
    job = store.create(model="m1", operation="op-obj", requested_duration_seconds=8)
    assert job.status == JobStatus.PENDING
    assert job.model == "m1"
    assert job.operation == "op-obj"
    assert job.requested_duration_seconds == 8
    assert job.job_id


def test_job_ids_are_unique() -> None:
    store = JobStore()
    a = store.create(model="m", operation=None)
    b = store.create(model="m", operation=None)
    assert a.job_id != b.job_id


def test_get_returns_created_job() -> None:
    store = JobStore()
    job = store.create(model="m", operation=None)
    got = store.get(job.job_id)
    assert got is not None
    assert got.job_id == job.job_id


def test_get_missing_returns_none() -> None:
    store = JobStore()
    assert store.get("no-such-id") is None


def test_update_persists_status_change() -> None:
    store = JobStore()
    job = store.create(model="m", operation=None)
    job.status = JobStatus.COMPLETE
    job.result_path = "/tmp/out.mp4"
    store.update(job)
    got = store.get(job.job_id)
    assert got is not None
    assert got.status == JobStatus.COMPLETE
    assert got.result_path == "/tmp/out.mp4"


def test_all_returns_newest_first() -> None:
    store = JobStore()
    first = store.create(model="m", operation=None)
    second = store.create(model="m", operation=None)
    jobs = store.all()
    assert [j.job_id for j in jobs] == [second.job_id, first.job_id]


def test_elapsed_seconds_non_negative() -> None:
    store = JobStore()
    job = store.create(model="m", operation=None)
    assert job.elapsed_seconds >= 0


def test_thread_safe_concurrent_writes() -> None:
    store = JobStore()
    created: list[str] = []
    created_lock = threading.Lock()

    def worker() -> None:
        for _ in range(50):
            j = store.create(model="m", operation=None)
            with created_lock:
                created.append(j.job_id)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(created) == 400
    assert len(set(created)) == 400
    assert len(store.all()) == 400
