import json
import redis.asyncio as aioredis
from config import REDIS_URL

_redis: aioredis.Redis | None = None


def _client() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(REDIS_URL, decode_responses=True)
    return _redis


async def get(key: str) -> dict | list | None:
    raw = await _client().get(key)
    return json.loads(raw) if raw else None


async def set(key: str, value: dict | list, ttl: int = 86400) -> None:
    await _client().setex(key, ttl, json.dumps(value))
