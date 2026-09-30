import json
import os
import sqlite3
import threading

BASE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("BENCH_DB", os.path.join(os.path.dirname(BASE), "data", "benchmark.db"))
_local = threading.local()


def conn():
    c = getattr(_local, "conn", None)
    if c is None:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        c = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA foreign_keys = ON")
        c.execute("PRAGMA journal_mode = WAL")
        _local.conn = c
    return c


def q(sql, args=()):
    return [dict(r) for r in conn().execute(sql, args).fetchall()]


def one(sql, args=()):
    r = conn().execute(sql, args).fetchone()
    return dict(r) if r else None


def exe(sql, args=()):
    c = conn()
    cur = c.execute(sql, args)
    c.commit()
    return cur.lastrowid


def insert(table, data):
    keys = list(data.keys())
    vals = [json.dumps(v) if isinstance(v, (dict, list)) else v for v in data.values()]
    return exe(f"INSERT INTO {table} ({','.join(keys)}) VALUES ({','.join('?' * len(keys))})", vals)


def update(table, id_, data, key="id"):
    if not data:
        return
    keys = list(data.keys())
    vals = [json.dumps(v) if isinstance(v, (dict, list)) else v for v in data.values()]
    exe(f"UPDATE {table} SET {','.join(k + '=?' for k in keys)} WHERE {key}=?", vals + [id_])


def audit(user_id, engagement_id, action, detail=""):
    exe("INSERT INTO audit_log (user_id, engagement_id, action, detail) VALUES (?,?,?,?)",
        (user_id, engagement_id, action, detail))


def setting(key, default=None):
    r = one("SELECT value FROM settings WHERE key=?", (key,))
    return r["value"] if r else default


MIGRATIONS = [  # columns added after v1.0 — applied to existing databases
    ("engagements", "requirements", "TEXT"), ("engagements", "key_questions", "TEXT"), ("engagements", "compare_what", "TEXT"),
    ("engagements", "analysis_method", "TEXT"), ("engagements", "analysis_rationale", "TEXT"),
    ("comparators", "role", "TEXT"), ("criteria", "scored", "INTEGER DEFAULT 1"), ("evidence", "author", "TEXT"),
]


def init():
    with open(os.path.join(BASE, "schema.sql"), encoding="utf-8") as f:
        conn().executescript(f.read())
    for table, col, typ in MIGRATIONS:
        if col not in {r["name"] for r in q(f"PRAGMA table_info({table})")}:
            conn().execute(f"ALTER TABLE {table} ADD COLUMN {col} {typ}")
    conn().commit()


def jl(v, default=None):
    """Parse a JSON column safely."""
    if v in (None, ""):
        return default if default is not None else []
    try:
        return json.loads(v)
    except (TypeError, ValueError):
        return default if default is not None else []
