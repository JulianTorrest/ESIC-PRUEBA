import hashlib
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

BASE_DIR = Path(__file__).resolve().parent
CACHE_DB = BASE_DIR / "data" / "cache.db"

# Intentar importar Redis, pero no es obligatorio
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class ResponseCache:
    """Caché de respuestas con soporte opcional a Redis y fallback a SQLite."""

    def __init__(self, ttl_seconds: int = 3600, redis_url: Optional[str] = None):
        self.ttl_seconds = ttl_seconds
        self.redis_url = redis_url
        self.redis_client = None
        self._init_sqlite()

        if REDIS_AVAILABLE and redis_url:
            try:
                self.redis_client = redis.Redis.from_url(redis_url, decode_responses=True)
                self.redis_client.ping()
            except Exception:
                self.redis_client = None

    def _init_sqlite(self):
        CACHE_DB.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(CACHE_DB)
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS cache (
                key TEXT PRIMARY KEY,
                value TEXT,
                expires_at TEXT
            )
            """
        )
        conn.commit()
        conn.close()

    @staticmethod
    def _make_key(query: str, provider: str, model: str) -> str:
        text = f"{query}|{provider}|{model}"
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    def get(self, query: str, provider: str, model: str) -> Optional[Any]:
        key = self._make_key(query, provider, model)

        if self.redis_client:
            try:
                value = self.redis_client.get(key)
                if value:
                    return json.loads(value)
            except Exception:
                pass

        conn = sqlite3.connect(CACHE_DB)
        cursor = conn.cursor()
        cursor.execute("SELECT value, expires_at FROM cache WHERE key = ?", (key,))
        row = cursor.fetchone()
        conn.close()

        if row:
            expires_at = datetime.fromisoformat(row[1])
            if datetime.now() < expires_at:
                return json.loads(row[0])
            self.delete(query, provider, model)
        return None

    def set(self, query: str, provider: str, model: str, value: Any):
        key = self._make_key(query, provider, model)
        serialized = json.dumps(value, ensure_ascii=False)
        expires_at = (datetime.now() + timedelta(seconds=self.ttl_seconds)).isoformat()

        if self.redis_client:
            try:
                self.redis_client.setex(key, self.ttl_seconds, serialized)
                return
            except Exception:
                pass

        conn = sqlite3.connect(CACHE_DB)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO cache (key, value, expires_at) VALUES (?, ?, ?)",
            (key, serialized, expires_at),
        )
        conn.commit()
        conn.close()

    def delete(self, query: str, provider: str, model: str):
        key = self._make_key(query, provider, model)

        if self.redis_client:
            try:
                self.redis_client.delete(key)
                return
            except Exception:
                pass

        conn = sqlite3.connect(CACHE_DB)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cache WHERE key = ?", (key,))
        conn.commit()
        conn.close()
