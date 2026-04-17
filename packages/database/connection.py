"""
Database connection management.
Supports both sync (for migrations/seeding) and async (for API).
"""

import asyncpg
import psycopg2
import psycopg2.extras
import json
import logging
from typing import Optional, Any
from contextlib import asynccontextmanager

from packages.core.config import settings

logger = logging.getLogger("grantpath.db")

# ─── Async Connection Pool (for API) ───

_pool: Optional[asyncpg.Pool] = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            settings.DATABASE_URL,
            min_size=2,
            max_size=10,
            command_timeout=30,
        )
        logger.info("Database connection pool created")
    return _pool


async def close_pool():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("Database connection pool closed")


@asynccontextmanager
async def get_connection():
    pool = await get_pool()
    async with pool.acquire() as conn:
        yield conn


async def execute(query: str, *args) -> str:
    async with get_connection() as conn:
        return await conn.execute(query, *args)


async def fetch(query: str, *args) -> list[asyncpg.Record]:
    async with get_connection() as conn:
        return await conn.fetch(query, *args)


async def fetchrow(query: str, *args) -> Optional[asyncpg.Record]:
    async with get_connection() as conn:
        return await conn.fetchrow(query, *args)


async def fetchval(query: str, *args) -> Any:
    async with get_connection() as conn:
        return await conn.fetchval(query, *args)


# ─── Sync Connection (for migrations/seeding) ───

class SyncDB:
    """Simple synchronous database wrapper for scripts."""

    def __init__(self, dsn: str = None):
        self.dsn = dsn or settings.DATABASE_URL
        self._conn = None

    def connect(self):
        self._conn = psycopg2.connect(self.dsn)
        self._conn.autocommit = True
        return self

    def close(self):
        if self._conn:
            self._conn.close()

    def execute(self, query: str, params: dict = None):
        with self._conn.cursor() as cur:
            cur.execute(query, params)

    def query(self, query: str, params: dict = None) -> list[dict]:
        with self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, params)
            return [dict(row) for row in cur.fetchall()]

    def query_one(self, query: str, params: dict = None) -> Optional[dict]:
        rows = self.query(query, params)
        return rows[0] if rows else None

    def __enter__(self):
        return self.connect()

    def __exit__(self, *args):
        self.close()
