import httpx
import pytest

from app.main import app

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32


def _client():
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def _create_dispute(client, entry) -> int:
    resp = await client.post(
        "/disputes",
        json={
            "trip_id": entry["trip_id"],
            "category": entry["category"],
            "claim_text": "attachment test claim",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def _cleanup(dispute_id: int) -> None:
    from sqlalchemy import delete

    from app.db import models
    from app.db.session import async_session_factory
    from app.queue.queue import remove_dispute

    await remove_dispute(dispute_id)
    async with async_session_factory() as session:
        await session.execute(delete(models.Attachment).where(models.Attachment.dispute_id == dispute_id))
        await session.execute(delete(models.Ruling).where(models.Ruling.dispute_id == dispute_id))
        await session.execute(delete(models.AgentMessage).where(models.AgentMessage.dispute_id == dispute_id))
        await session.execute(delete(models.Dispute).where(models.Dispute.id == dispute_id))
        await session.commit()


def _resolve_env(monkeypatch):
    from app.llm.client import client

    monkeypatch.setattr(client, "mock", True)

    async def fake_retrieve(query, category=None, k=4, session=None):
        return []

    monkeypatch.setattr("app.agents.base.retrieve_policy", fake_retrieve)
    monkeypatch.setattr("app.orchestrator.pipeline.retrieve_policy", fake_retrieve)


async def test_upload_allowed_and_rejected_types(seeded_session, ground_truth):
    entry = next(e for e in ground_truth if e["label"] == "route_deviation")
    dispute_id = None
    try:
        async with _client() as client:
            dispute_id = await _create_dispute(client, entry)

            ok = await client.post(
                f"/disputes/{dispute_id}/attachments",
                files={"file": ("photo.png", PNG_BYTES, "image/png")},
                data={"kind": "photo"},
            )
            assert ok.status_code == 201, ok.text

            bad = await client.post(
                f"/disputes/{dispute_id}/attachments",
                files={"file": ("evil.exe", b"MZ", "application/x-msdownload")},
                data={"kind": "other"},
            )
            assert bad.status_code == 415
    finally:
        if dispute_id is not None:
            await _cleanup(dispute_id)


async def test_upload_size_cap(seeded_session, ground_truth):
    entry = next(e for e in ground_truth if e["label"] == "route_deviation")
    dispute_id = None
    try:
        async with _client() as client:
            dispute_id = await _create_dispute(client, entry)
            big = b"\x00" * (5 * 1024 * 1024 + 1)
            resp = await client.post(
                f"/disputes/{dispute_id}/attachments",
                files={"file": ("big.png", big, "image/png")},
                data={"kind": "photo"},
            )
            assert resp.status_code == 413
    finally:
        if dispute_id is not None:
            await _cleanup(dispute_id)


async def test_upload_duplicate_hash(seeded_session, ground_truth):
    entry = next(e for e in ground_truth if e["label"] == "route_deviation")
    dispute_id = None
    try:
        async with _client() as client:
            dispute_id = await _create_dispute(client, entry)
            first = await client.post(
                f"/disputes/{dispute_id}/attachments",
                files={"file": ("photo.png", PNG_BYTES, "image/png")},
                data={"kind": "photo"},
            )
            assert first.status_code == 201, first.text

            dup = await client.post(
                f"/disputes/{dispute_id}/attachments",
                files={"file": ("photo.png", PNG_BYTES, "image/png")},
                data={"kind": "photo"},
            )
            assert dup.status_code == 409
    finally:
        if dispute_id is not None:
            await _cleanup(dispute_id)


async def test_attachment_evidence_created_and_registered(seeded_session, ground_truth, monkeypatch):
    from app.orchestrator.pipeline import resolve_dispute

    _resolve_env(monkeypatch)

    entry = next(e for e in ground_truth if e["label"] == "route_deviation")
    dispute_id = None
    attachment_id = None
    try:
        async with _client() as client:
            dispute_id = await _create_dispute(client, entry)
            up = await client.post(
                f"/disputes/{dispute_id}/attachments",
                files={"file": ("receipt.png", PNG_BYTES, "image/png")},
                data={"kind": "receipt"},
            )
            assert up.status_code == 201, up.text
            attachment_id = up.json()["id"]

            ruling = await resolve_dispute(dispute_id, rebuttal=False)
            assert ruling.id is not None

            messages = (await client.get(f"/disputes/{dispute_id}/messages")).json()
            rider = next(m for m in messages if m["sender"] == "RiderAdvocate" and m["message_type"] == "case_brief")
            assert f"attachment_analysis:{attachment_id}" in rider["content"]["evidence_ids"]

            attachment_items = [
                e for e in rider["content"]["evidence"] if e["type"] == "attachment_analysis"
            ]
            assert len(attachment_items) == 1
            item = attachment_items[0]
            assert item["id"] == f"attachment_analysis:{attachment_id}"
            assert item["supports"] == "neutral"
            assert item["strength"] <= 0.5
            assert item["summary"].startswith("User-supplied, unverified:")
            assert item["data"]["attachment_id"] == attachment_id
            assert item["data"]["sha256"]
    finally:
        if dispute_id is not None:
            await _cleanup(dispute_id)


async def test_ruling_identical_with_and_without_attachment(seeded_session, ground_truth, monkeypatch):
    from app.orchestrator.pipeline import resolve_dispute

    _resolve_env(monkeypatch)

    entry = next(e for e in ground_truth if e["label"] == "route_deviation")
    ids = []
    try:
        async with _client() as client:
            plain_id = await _create_dispute(client, entry)
            ids.append(plain_id)
            plain_ruling = await resolve_dispute(plain_id, rebuttal=False)

            with_attachment_id = await _create_dispute(client, entry)
            ids.append(with_attachment_id)
            await client.post(
                f"/disputes/{with_attachment_id}/attachments",
                files={"file": ("photo.png", PNG_BYTES, "image/png")},
                data={"kind": "photo"},
            )
            with_attachment_ruling = await resolve_dispute(with_attachment_id, rebuttal=False)

        assert plain_ruling.outcome == with_attachment_ruling.outcome
        assert plain_ruling.refund_amount == with_attachment_ruling.refund_amount
    finally:
        for dispute_id in ids:
            await _cleanup(dispute_id)
