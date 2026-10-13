import json
import logging

import redis.asyncio as aioredis

from app.config import settings

logger = logging.getLogger(__name__)

DEFAULT_CHANNEL = "agent_messages"


def dispute_channel(dispute_id: int) -> str:
    return f"dispute:{dispute_id}"


async def publish_message(channel: str, payload: dict) -> None:
    try:
        client = aioredis.from_url(settings.redis_url, decode_responses=True)
        await client.publish(channel, json.dumps(payload, default=str))
        await client.aclose()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to publish message to Redis: %s", exc)


async def publish_dispute_event(dispute_id: int, event_type: str, data: dict | None = None) -> None:
    await publish_message(
        dispute_channel(dispute_id),
        {"dispute_id": dispute_id, "type": event_type, "data": data or {}},
    )
