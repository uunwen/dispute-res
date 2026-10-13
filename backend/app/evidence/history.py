import datetime as dt

from sqlalchemy import select

from app.db import models
from app.db.enums import RulingOutcome
from app.db.session import async_session_factory
from app.evidence.base import result_to_evidence
from app.schemas.evidence import EvidenceItem

_DISPUTE_REF = 8.0

_FAVORABLE_RIDER = {RulingOutcome.full_refund, RulingOutcome.partial_refund, RulingOutcome.favor_rider}
_FAVORABLE_DRIVER = {RulingOutcome.no_refund, RulingOutcome.favor_driver}


def compute_history_profile(account, dispute_count, won_count, resolved_count, *, now=None):
    """Compute an abuse-risk profile from an account's dispute history.

    The score is a weighted combination (weights documented inline):

    * 0.50 * dispute factor, where ``dispute_factor = min(1, dispute_count / 8)``;
    * 0.25 * loss factor, ``1 - win_rate`` (neutral 0.5 when nothing is resolved);
    * 0.25 * rating factor, ``max(0, 1 - rating / 5)``.

    All inputs are plain numbers, so this function is pure and deterministic.
    """
    now = now or dt.datetime.now(dt.timezone.utc)
    dispute_factor = min(1.0, dispute_count / _DISPUTE_REF)
    win_rate = (won_count / resolved_count) if resolved_count else 0.5
    rating_factor = max(0.0, 1.0 - account.rating / 5.0)
    abuse_risk = round(0.5 * dispute_factor + 0.25 * (1.0 - win_rate) + 0.25 * rating_factor, 3)

    account_age_days = max(0, (now - account.created_at).days)

    data = {
        "account_id": account.id,
        "name": account.name,
        "role": account.role.value,
        "rating": account.rating,
        "account_age_days": account_age_days,
        "dispute_count": dispute_count,
        "resolved_count": resolved_count,
        "won_count": won_count,
        "win_rate": round(win_rate, 3),
        "abuse_risk_score": abuse_risk,
    }

    summary = (
        f"Account has {dispute_count} disputes, {win_rate:.0%} win rate, "
        f"abuse-risk score {abuse_risk:.2f}."
    )
    return {
        "supports": "neutral",
        "strength": abuse_risk,
        "summary": summary,
        "data": data,
    }


async def compute_history_profile_db(account_id: int, session=None) -> EvidenceItem:
    async def _run(s):
        account = (
            await s.execute(select(models.Account).where(models.Account.id == account_id))
        ).scalar_one_or_none()
        if account is None:
            raise ValueError(f"account {account_id} not found")

        dispute_count = (
            await s.execute(
                select(models.Dispute).where(models.Dispute.filed_by == account_id)
            )
        ).scalars().all()
        total = len(dispute_count)

        dispute_ids = [d.id for d in dispute_count]
        resolved = 0
        won = 0
        if dispute_ids:
            favorable = _FAVORABLE_DRIVER if account.role.value == "driver" else _FAVORABLE_RIDER
            rulings = (
                await s.execute(
                    select(models.Ruling).where(models.Ruling.dispute_id.in_(dispute_ids))
                )
            ).scalars().all()
            resolved = len(rulings)
            won = sum(1 for r in rulings if r.outcome in favorable)

        result = compute_history_profile(account, total, won, resolved)
        return result_to_evidence("history_profile", account_id, None, result)

    if session is not None:
        return await _run(session)
    async with async_session_factory() as s:
        return await _run(s)
