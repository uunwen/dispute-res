import json
from pathlib import Path

import pytest
from sqlalchemy import text

from app.db.session import async_session_factory

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


@pytest.fixture(scope="session")
def ground_truth():
    return json.loads((DATA_DIR / "ground_truth.json").read_text(encoding="utf-8"))


@pytest.fixture
async def seeded_session():
    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
            yield session
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Database unavailable: {exc}")


def trip_id_for(gt, label):
    return next(e["trip_id"] for e in gt if e["label"] == label)
