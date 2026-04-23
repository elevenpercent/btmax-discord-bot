"""
api_client.py — Central API module.
Handles all HTTP logic, rate-limit enforcement, caching, and 429 retry.

Rate limit: 1 request per 5 seconds (12/min global budget).
"""

import asyncio
import logging
import time
from typing import Any, Optional

import aiohttp

logger = logging.getLogger("btmax.api")

# ── TTL constants (seconds) ────────────────────────────────────
TTL_CHALLENGE  = 300    # 5 min
TTL_LB_TODAY   = 60     # 1 min  — live data
TTL_LB_PAST    = 86400  # 24 hr  — historical, never changes
TTL_LIFETIME   = 300    # 5 min
TTL_SEARCH     = 300    # 5 min
TTL_USER_STATS = 300    # 5 min


class APIClient:
    """
    Thread-safe, concurrency-safe API client with:
    - Serialised request queue (enforces 5s spacing)
    - TTL-based in-memory cache
    - Graceful 429 handling with Retry-After support
    - Automatic retry on transient 5xx errors
    - Structured performance logging
    """

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key  = api_key
        self._cache: dict[str, tuple[Any, float]] = {}
        self._lock   = asyncio.Lock()
        self._last   = 0.0
        self._session: Optional[aiohttp.ClientSession] = None

        # Performance counters
        self._hits   = 0
        self._misses = 0
        self._errors = 0

    async def start(self):
        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=10)
        )
        logger.info("API client ready. Base URL: %s", self.base_url)

    async def close(self):
        if self._session:
            await self._session.close()
        logger.info(
            "API client closed. Cache hits=%d misses=%d errors=%d",
            self._hits, self._misses, self._errors
        )

    # ── Cache ──────────────────────────────────────────────────
    def _get(self, key: str) -> Optional[Any]:
        entry = self._cache.get(key)
        if entry and time.monotonic() < entry[1]:
            self._hits += 1
            logger.debug("Cache HIT  key=%s", key)
            return entry[0]
        self._misses += 1
        logger.debug("Cache MISS key=%s", key)
        return None

    def _set(self, key: str, data: Any, ttl: int):
        self._cache[key] = (data, time.monotonic() + ttl)

    # ── HTTP ───────────────────────────────────────────────────
    async def _request(self, path: str, params: dict = None) -> Any:
        async with self._lock:
            # Enforce 5-second gap between requests
            elapsed = time.monotonic() - self._last
            if self._last > 0 and elapsed < 5.0:
                wait = 5.0 - elapsed
                logger.debug("Rate-limit spacing: sleeping %.2fs", wait)
                await asyncio.sleep(wait)

            url = f"{self.base_url}{path}"
            headers = {"X-API-Key": self.api_key}
            t0 = time.monotonic()

            for attempt in range(2):
                try:
                    async with self._session.get(
                        url, params=params or {}, headers=headers
                    ) as resp:
                        latency = (time.monotonic() - t0) * 1000

                        if resp.status == 429:
                            retry_after = int(resp.headers.get("Retry-After", 5))
                            logger.warning(
                                "429 Rate-limited on %s — waiting %ds (attempt %d)",
                                path, retry_after, attempt + 1
                            )
                            if attempt == 0:
                                await asyncio.sleep(retry_after)
                                continue
                            self._errors += 1
                            raise RuntimeError("Rate limited after retry.")

                        if resp.status >= 500:
                            logger.error("5xx error %d on %s", resp.status, path)
                            if attempt == 0:
                                await asyncio.sleep(2)
                                continue
                            self._errors += 1
                            raise RuntimeError(f"Server error: {resp.status}")

                        resp.raise_for_status()
                        data = await resp.json()
                        self._last = time.monotonic()
                        logger.info(
                            "GET %s → %d  %.0fms",
                            path, resp.status, latency
                        )
                        return data

                except aiohttp.ClientError as e:
                    self._errors += 1
                    raise RuntimeError(f"Connection error: {e}") from e

    # ── Public API methods ─────────────────────────────────────
    async def get_daily_challenge(self) -> dict:
        key = "challenge"
        cached = self._get(key)
        if cached is not None:
            return cached
        data = await self._request("/daily_challenge")
        self._set(key, data, TTL_CHALLENGE)
        return data

    async def get_leaderboard(self, date: str, limit: int = 10) -> list:
        from datetime import datetime
        today = datetime.utcnow().strftime("%Y-%m-%d")
        key   = f"lb:{date}:{limit}"
        cached = self._get(key)
        if cached is not None:
            return cached
        data = await self._request(
            "/daily_challenge/leaderboard",
            {"date": date, "limit": limit}
        )
        self._set(key, data, TTL_LB_TODAY if date == today else TTL_LB_PAST)
        return data

    async def get_lifetime(self) -> list:
        key = "lifetime"
        cached = self._get(key)
        if cached is not None:
            return cached
        data = await self._request("/daily_challenge/lifetime")
        self._set(key, data, TTL_LIFETIME)
        return data

    async def search_users(self, query: str) -> list:
        key = f"search:{query.lower()}"
        cached = self._get(key)
        if cached is not None:
            return cached
        data = await self._request("/users/search", {"q": query})
        self._set(key, data, TTL_SEARCH)
        return data

    async def get_user_stats(self, user_id: str) -> dict:
        key = f"stats:{user_id}"
        cached = self._get(key)
        if cached is not None:
            return cached
        data = await self._request(f"/users/{user_id}/daily_challenge_stats")
        self._set(key, data, TTL_USER_STATS)
        return data
