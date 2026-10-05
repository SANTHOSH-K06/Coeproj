"""Single-process background jobs for periodic metrics and configured retention."""

import asyncio
import logging
import os

from .database import SessionLocal
from .retention import purge_expired_records
from .storage_history import capture_storage_snapshot

logger = logging.getLogger(__name__)


def _capture_snapshot_job() -> None:
    with SessionLocal() as db:
        capture_storage_snapshot(db)


def _retention_job() -> None:
    with SessionLocal() as db:
        result = purge_expired_records(db, dry_run=False)
        logger.info(
            "Retention job finished: removed %s appointments and %s slots",
            result["deleted_appointments"],
            result["deleted_slots"],
        )


async def _periodic_job(name: str, interval: int, callback) -> None:
    while True:
        await asyncio.sleep(interval)
        try:
            await asyncio.to_thread(callback)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Periodic %s job failed", name)


def start_background_jobs() -> list[asyncio.Task]:
    """Start periodic tasks; intervals are configurable for deployment/testing."""
    snapshot_interval = max(60, int(os.getenv("STORAGE_SNAPSHOT_INTERVAL_SECONDS", "3600")))
    tasks = [asyncio.create_task(_periodic_job("storage snapshot", snapshot_interval, _capture_snapshot_job))]
    if os.getenv("RETENTION_PURGE_ENABLED", "true").lower() in {"1", "true", "yes", "on"}:
        retention_interval = max(60, int(os.getenv("RETENTION_PURGE_INTERVAL_SECONDS", "86400")))
        tasks.append(asyncio.create_task(_periodic_job("retention purge", retention_interval, _retention_job)))
    return tasks


async def stop_background_jobs(tasks: list[asyncio.Task]) -> None:
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
