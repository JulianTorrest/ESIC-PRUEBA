import json
import sqlite3
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

BASE_DIR = Path(__file__).resolve().parent
OBS_DB = BASE_DIR / "data" / "observability.db"

# Costos aproximados por 1K tokens (entrada/salida) en USD
# Valores ilustrativos, ajustar según tarifas reales
COST_RATES = {
    "openai": {
        "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
        "gpt-4": {"input": 0.03, "output": 0.06},
    },
    "mistral": {
        "mistral-tiny": {"input": 0.0002, "output": 0.0006},
        "mistral-small": {"input": 0.002, "output": 0.006},
        "mistral-medium": {"input": 0.006, "output": 0.018},
    },
    "groq": {
        "llama3-8b-8192": {"input": 0.0001, "output": 0.0002},
        "mixtral-8x7b-32768": {"input": 0.0005, "output": 0.0008},
    },
    "local": {
        "local": {"input": 0.0, "output": 0.0},
    },
}


def _seed_dummy_traces():
    """Inserta trazas ilustrativas si la base esta vacia."""
    conn = sqlite3.connect(OBS_DB)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM llm_traces")
    if cursor.fetchone()[0] > 0:
        conn.close()
        return

    now = datetime.now()
    for i in range(1, 13):
        provider = ["openai", "mistral", "groq", "local"][i % 4]
        model = list(COST_RATES[provider].keys())[0]
        prompt = "Consulta de ejemplo"
        response = "Respuesta de ejemplo"
        prompt_tokens = 120 + i * 10
        completion_tokens = 80 + i * 5
        total = prompt_tokens + completion_tokens
        latency = 250 + i * 30
        cost = estimate_cost(provider, model, prompt_tokens, completion_tokens)
        cursor.execute(
            "INSERT INTO llm_traces (trace_id, session_id, provider, model, prompt, response, prompt_tokens, completion_tokens, total_tokens, latency_ms, estimated_cost_usd, status, error_message, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (f"TRACE-{i:04d}", "demo", provider, model, prompt, response, prompt_tokens, completion_tokens, total, latency, cost, "ok", "", (now - timedelta(hours=i)).isoformat()),
        )
    conn.commit()
    conn.close()


def _init_db():
    OBS_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(OBS_DB)
    cursor = conn.cursor()
    cursor.executescript(
        """
        CREATE TABLE IF NOT EXISTS llm_traces (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trace_id TEXT UNIQUE,
            session_id TEXT,
            provider TEXT,
            model TEXT,
            prompt TEXT,
            response TEXT,
            prompt_tokens INTEGER,
            completion_tokens INTEGER,
            total_tokens INTEGER,
            latency_ms INTEGER,
            estimated_cost_usd REAL,
            status TEXT,
            error_message TEXT,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trace_id TEXT,
            session_id TEXT,
            rating INTEGER,
            comment TEXT,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS rate_limits_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            ip TEXT,
            created_at TEXT
        );
        """
    )
    conn.commit()
    conn.close()


_init_db()


def count_tokens(text: str) -> int:
    """Estimación simple de tokens: ~4 caracteres por token."""
    return max(1, len(text) // 4)


def estimate_cost(provider: str, model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Estima costo en USD de una llamada a LLM."""
    provider_rates = COST_RATES.get(provider, {})
    rates = provider_rates.get(model, {"input": 0.0, "output": 0.0})
    cost = (prompt_tokens / 1000) * rates["input"] + (completion_tokens / 1000) * rates["output"]
    return round(cost, 6)


def log_llm_call(
    session_id: str,
    provider: str,
    model: str,
    prompt: str,
    response: str,
    latency_ms: int,
    status: str = "ok",
    error_message: str = "",
) -> str:
    """Registra una llamada a LLM con métricas de FinOps."""
    trace_id = f"TRACE-{uuid.uuid4().hex[:8].upper()}"
    prompt_tokens = count_tokens(prompt)
    completion_tokens = count_tokens(response)
    total_tokens = prompt_tokens + completion_tokens
    cost = estimate_cost(provider, model, prompt_tokens, completion_tokens)

    conn = sqlite3.connect(OBS_DB)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO llm_traces (trace_id, session_id, provider, model, prompt, response,
                                prompt_tokens, completion_tokens, total_tokens, latency_ms,
                                estimated_cost_usd, status, error_message, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            trace_id, session_id, provider, model, prompt, response,
            prompt_tokens, completion_tokens, total_tokens, latency_ms,
            cost, status, error_message, datetime.now().isoformat(),
        ),
    )
    conn.commit()
    conn.close()
    return trace_id


def get_traces(limit: int = 100) -> List[Dict[str, Any]]:
    conn = sqlite3.connect(OBS_DB)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT trace_id, session_id, provider, model, prompt_tokens, completion_tokens, total_tokens, "
        "latency_ms, estimated_cost_usd, status, created_at FROM llm_traces ORDER BY id DESC LIMIT ?",
        (limit,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "trace_id": r[0],
            "session_id": r[1],
            "provider": r[2],
            "model": r[3],
            "prompt_tokens": r[4],
            "completion_tokens": r[5],
            "total_tokens": r[6],
            "latency_ms": r[7],
            "cost_usd": r[8],
            "status": r[9],
            "created_at": r[10],
        }
        for r in rows
    ]


def finops_summary() -> Dict[str, Any]:
    conn = sqlite3.connect(OBS_DB)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT provider, SUM(total_tokens), SUM(estimated_cost_usd), COUNT(*), AVG(latency_ms) "
        "FROM llm_traces GROUP BY provider"
    )
    rows = cursor.fetchall()
    conn.close()
    return {
        r[0]: {
            "total_tokens": r[1] or 0,
            "total_cost_usd": round(r[2] or 0, 4),
            "calls": r[3] or 0,
            "avg_latency_ms": round(r[4] or 0, 2),
        }
        for r in rows
    }


def save_feedback(trace_id: str, session_id: str, rating: int, comment: str = ""):
    conn = sqlite3.connect(OBS_DB)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO feedback (trace_id, session_id, rating, comment, created_at) VALUES (?, ?, ?, ?, ?)",
        (trace_id, session_id, rating, comment, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


def feedback_stats() -> Dict[str, Any]:
    conn = sqlite3.connect(OBS_DB)
    cursor = conn.cursor()
    cursor.execute("SELECT rating, COUNT(*) FROM feedback GROUP BY rating")
    rows = cursor.fetchall()
    conn.close()
    return {"total": sum(r[1] for r in rows), "by_rating": {r[0]: r[1] for r in rows}}


def rate_limit_check(session_id: str, ip: str = None, max_per_minute: int = 10, max_per_hour: int = 100) -> bool:
    """Ventana deslizante: maximo por minuto y por hora."""
    now = datetime.now()
    one_min_ago = (now - timedelta(minutes=1)).isoformat()
    one_hour_ago = (now - timedelta(hours=1)).isoformat()

    conn = sqlite3.connect(OBS_DB)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO rate_limits_log (session_id, ip, created_at) VALUES (?, ?, ?)",
        (session_id, ip or "", now.isoformat()),
    )
    conn.commit()

    cursor.execute(
        "SELECT COUNT(*) FROM rate_limits_log WHERE session_id = ? AND created_at > ?",
        (session_id, one_min_ago),
    )
    per_min = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM rate_limits_log WHERE session_id = ? AND created_at > ?",
        (session_id, one_hour_ago),
    )
    per_hour = cursor.fetchone()[0]

    if ip:
        cursor.execute(
            "SELECT COUNT(*) FROM rate_limits_log WHERE ip = ? AND created_at > ?",
            (ip, one_min_ago),
        )
        ip_per_min = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(*) FROM rate_limits_log WHERE ip = ? AND created_at > ?",
            (ip, one_hour_ago),
        )
        ip_per_hour = cursor.fetchone()[0]
    else:
        ip_per_min = 0
        ip_per_hour = 0

    conn.close()
    return per_min <= max_per_minute and per_hour <= max_per_hour and ip_per_min <= max_per_minute and ip_per_hour <= max_per_hour


_seed_dummy_traces()
