from sqlalchemy import select
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from app.db import models
from app.db.session import async_session_factory
from app.evidence.base import result_to_evidence
from app.llm.client import client as llm_client
from app.schemas.evidence import ChatInsights, EvidenceItem

_analyzer = SentimentIntensityAnalyzer()

_CACHE: dict[int, EvidenceItem] = {}

_SYSTEM_PROMPT = (
    "You are analysing a ride-hailing chat log. Extract the requested facts and "
    "for each one cite the message ID(s) it comes from. Respond with JSON only."
)


def normalize(messages):
    """Strip whitespace and drop empty/duplicate consecutive messages.

    ``messages`` is a list of ``(message_id, text)`` tuples.
    """
    out = []
    for mid, text in messages:
        s = text.strip()
        if not s:
            continue
        if out and out[-1][1] == s:
            continue
        out.append((mid, s))
    return out


def vader_sentiment(texts):
    """Return average VADER sentiment plus per-message scores for ``texts``."""
    if not texts:
        return {
            "compound": 0.0,
            "neg": 0.0,
            "neu": 0.0,
            "pos": 0.0,
            "per_message": [],
        }
    scores = [_analyzer.polarity_scores(t) for t in texts]
    avg = {k: round(sum(s[k] for s in scores) / len(scores), 4) for k in ("neg", "neu", "pos", "compound")}
    per_message = [
        {"text": texts[i], "compound": round(scores[i]["compound"], 4)} for i in range(len(texts))
    ]
    return {
        "compound": avg["compound"],
        "neg": avg["neg"],
        "neu": avg["neu"],
        "pos": avg["pos"],
        "per_message": per_message,
    }


async def analyze_chat(trip_id: int, session=None) -> EvidenceItem:
    if trip_id in _CACHE:
        return _CACHE[trip_id]

    async def _run(s):
        rows = (
            await s.execute(
                select(models.ChatMessage.id, models.ChatMessage.text)
                .where(models.ChatMessage.trip_id == trip_id)
                .order_by(models.ChatMessage.ts)
            )
        ).all()
        return [(r[0], r[1]) for r in rows]

    if session is not None:
        messages = await _run(session)
    else:
        async with async_session_factory() as s:
            messages = await _run(s)

    normalized = normalize(messages)
    texts = [t for _mid, t in normalized]
    sentiment = vader_sentiment(texts)

    insights: ChatInsights | None = None
    llm_error = None
    if llm_client.configured and texts:
        user_prompt = "\n".join(f"{mid}: {text}" for mid, text in normalized)
        try:
            insights = await llm_client.structured(_SYSTEM_PROMPT, user_prompt, ChatInsights)
        except Exception as exc:  # noqa: BLE001
            llm_error = str(exc)

    insight_dict = insights.model_dump() if insights is not None else None

    data = {
        "message_count": len(messages),
        "normalized_message_count": len(normalized),
        "sentiment": sentiment,
        "threats_count": len(insight_dict["threats"]) if insight_dict else 0,
        "admissions_count": len(insight_dict["admissions"]) if insight_dict else 0,
        "llm_used": insights is not None,
        "llm_error": llm_error,
        "insights": insight_dict,
    }

    compound = sentiment["compound"]
    result = {
        "supports": "neutral",
        "strength": min(1.0, 0.3 + abs(compound)),
        "summary": f"Chat analysis: {len(messages)} messages, avg sentiment {compound:.2f}.",
        "data": data,
    }

    evidence = result_to_evidence("chat_analysis", trip_id, trip_id, result)
    _CACHE[trip_id] = evidence
    return evidence


def clear_cache() -> None:
    _CACHE.clear()
