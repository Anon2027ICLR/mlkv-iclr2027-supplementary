"""Resumable SQLite result store.

One row per generation, keyed by a deterministic run_key so re-running a
matrix skips completed cells. The serving stack (library versions, device,
dtype) is recorded per batch of runs — the HindsightBench lesson: behavior
differs across serving configurations, so comparisons must be stack-pinned.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from mlkv.languages import PROMPT_VERSION

SCHEMA = """
CREATE TABLE IF NOT EXISTS generations (
    run_key TEXT PRIMARY KEY,
    model TEXT NOT NULL,
    task TEXT NOT NULL,
    lang TEXT NOT NULL,
    config TEXT NOT NULL,
    item_id TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    stack_id TEXT NOT NULL,
    output TEXT,
    n_output_tokens INTEGER,
    output_bytes INTEGER,
    answer_gold TEXT,
    correct INTEGER,
    drift REAL,
    latency_s REAL,
    meta TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_gen_cell ON generations(model, task, lang, config);

CREATE TABLE IF NOT EXISTS stacks (
    stack_id TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def run_key(model: str, task: str, lang: str, config: str, item_id: str) -> str:
    raw = "|".join([model, task, lang, config, str(item_id), PROMPT_VERSION])
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def connect(path: str | Path = "results/mlkv.db") -> sqlite3.Connection:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def register_stack(conn: sqlite3.Connection, description: dict) -> str:
    """Record the serving stack (versions, device, dtype); return its id."""
    payload = json.dumps(description, sort_keys=True)
    stack_id = hashlib.sha256(payload.encode()).hexdigest()[:12]
    conn.execute(
        "INSERT OR IGNORE INTO stacks (stack_id, description, created_at) VALUES (?, ?, ?)",
        (stack_id, payload, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    return stack_id


def is_done(conn: sqlite3.Connection, key: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM generations WHERE run_key = ?", (key,)
    ).fetchone() is not None


def save(conn: sqlite3.Connection, key: str, *, model: str, task: str, lang: str,
         config: str, item_id: str, stack_id: str, output: str,
         n_output_tokens: int, answer_gold: str, correct: bool,
         drift: float | None, latency_s: float, meta: dict | None = None) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO generations (
            run_key, model, task, lang, config, item_id, prompt_version,
            stack_id, output, n_output_tokens, output_bytes, answer_gold,
            correct, drift, latency_s, meta, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            key, model, task, lang, config, str(item_id), PROMPT_VERSION,
            stack_id, output, n_output_tokens, len(output.encode("utf-8")),
            str(answer_gold), int(correct), drift, latency_s,
            json.dumps(meta or {}), datetime.now(timezone.utc).isoformat(),
        ),
    )
    conn.commit()


def summary(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT model, task, lang, config,
               COUNT(*) AS n,
               AVG(correct) AS accuracy,
               AVG(n_output_tokens) AS avg_tokens,
               AVG(output_bytes) AS avg_bytes,
               AVG(drift) AS avg_drift
        FROM generations
        GROUP BY model, task, lang, config
        ORDER BY model, task, config, lang
        """
    ).fetchall()
