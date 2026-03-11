"""
Analytics service -- SQLite event storage + in-memory active users
"""
import json
import os
import random
import sqlite3
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from fastapi import Request

import config

_db_path = config.ANALYTICS_DB_PATH

# In-memory active user tracking: ip -> {ts: float, username: str|None}
_active_users: Dict[str, dict] = {}
_ACTIVE_TIMEOUT = 120  # seconds


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    os.makedirs(os.path.dirname(_db_path), exist_ok=True)
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            event_type TEXT NOT NULL,
            ip TEXT,
            metadata TEXT,
            username TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
        CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);

        CREATE TABLE IF NOT EXISTS chat_feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT DEFAULT (datetime('now', 'localtime')),
            username TEXT,
            conversation_id TEXT,
            question TEXT,
            answer_preview TEXT,
            feedback TEXT NOT NULL,
            route TEXT,
            confidence TEXT,
            model TEXT,
            sources_count INTEGER DEFAULT 0
        );
        CREATE INDEX IF NOT EXISTS idx_feedback_timestamp ON chat_feedback(timestamp);
    """)
    # Migration: add username column to existing DB if not present
    try:
        conn.execute("ALTER TABLE events ADD COLUMN username TEXT")
        conn.commit()
    except Exception:
        pass  # Column already exists
    conn.close()


# -- Client IP ----------------------------------------------------------------

def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


# -- Record -------------------------------------------------------------------

def record_heartbeat(ip: str, username: Optional[str] = None):
    now = time.time()
    prev = _active_users.get(ip)
    is_new_visit = prev is None or (now - prev["ts"]) > _ACTIVE_TIMEOUT
    _active_users[ip] = {"ts": now, "username": username}
    # Record a page_visit event only on new sessions (first heartbeat or after timeout)
    if is_new_visit:
        record_event("visit", ip, None, username=username)


def record_event(event_type: str, ip: str, metadata: Optional[dict], username: Optional[str] = None):
    conn = _get_conn()
    try:
        conn.execute(
            "INSERT INTO events (event_type, ip, metadata, username) VALUES (?, ?, ?, ?)",
            (event_type, ip, json.dumps(metadata, ensure_ascii=False) if metadata else None, username),
        )
        conn.commit()
    finally:
        conn.close()


# -- Query: Active users ------------------------------------------------------

def get_active_user_count() -> int:
    now = time.time()
    _cleanup_expired(now)
    return len(_active_users)


def get_active_user_list() -> List[dict]:
    """Return list of active users with IP, username, and last seen timestamp."""
    now = time.time()
    _cleanup_expired(now)
    result = []
    for ip, data in sorted(_active_users.items(), key=lambda x: x[1]["ts"], reverse=True):
        elapsed = int(now - data["ts"])
        result.append({"ip": ip, "elapsed_sec": elapsed, "username": data.get("username")})
    return result


def _cleanup_expired(now: float):
    expired = [ip for ip, data in _active_users.items() if now - data["ts"] > _ACTIVE_TIMEOUT]
    for ip in expired:
        del _active_users[ip]


# -- Query: Visitors -----------------------------------------------------------

def get_today_visitors() -> int:
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT COUNT(DISTINCT ip) AS cnt FROM events WHERE event_type='visit' AND date(timestamp)=date('now','localtime')"
        ).fetchone()
        return row["cnt"] if row else 0
    finally:
        conn.close()


def get_week_visitors() -> int:
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT COUNT(DISTINCT ip) AS cnt FROM events WHERE event_type='visit' AND timestamp >= datetime('now','localtime','-7 days')"
        ).fetchone()
        return row["cnt"] if row else 0
    finally:
        conn.close()


def get_total_visitors() -> int:
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT COUNT(DISTINCT ip) AS cnt FROM events WHERE event_type='visit'"
        ).fetchone()
        return row["cnt"] if row else 0
    finally:
        conn.close()


def get_daily_visitors(days: int = 14) -> List[dict]:
    conn = _get_conn()
    try:
        rows = conn.execute("""
            SELECT date(timestamp) AS day, COUNT(DISTINCT ip) AS cnt
            FROM events
            WHERE event_type='visit' AND timestamp >= datetime('now','localtime',?)
            GROUP BY day ORDER BY day
        """, (f"-{days} days",)).fetchall()
        return [{"day": r["day"], "count": r["cnt"]} for r in rows]
    finally:
        conn.close()


# -- Query: Top pages ----------------------------------------------------------

def get_top_pages(limit: int = 10) -> List[dict]:
    conn = _get_conn()
    try:
        rows = conn.execute("""
            SELECT json_extract(metadata, '$.url') AS url, COUNT(*) AS cnt
            FROM events
            WHERE event_type='page_view' AND metadata IS NOT NULL
            GROUP BY url ORDER BY cnt DESC LIMIT ?
        """, (limit,)).fetchall()
        return [{"url": r["url"], "count": r["cnt"]} for r in rows]
    finally:
        conn.close()


# -- Query: Top searches -------------------------------------------------------

def get_top_searches(limit: int = 10) -> List[dict]:
    conn = _get_conn()
    try:
        rows = conn.execute("""
            SELECT json_extract(metadata, '$.query') AS query, COUNT(*) AS cnt
            FROM events
            WHERE event_type='search' AND metadata IS NOT NULL
            GROUP BY query ORDER BY cnt DESC LIMIT ?
        """, (limit,)).fetchall()
        return [{"query": r["query"], "count": r["cnt"]} for r in rows]
    finally:
        conn.close()


# -- Query: Chat stats ---------------------------------------------------------

def get_chat_stats() -> dict:
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT COUNT(*) AS total FROM events WHERE event_type='chat'"
        ).fetchone()
        total = row["total"] if row else 0

        today_row = conn.execute(
            "SELECT COUNT(*) AS cnt FROM events WHERE event_type='chat' AND date(timestamp)=date('now','localtime')"
        ).fetchone()
        today = today_row["cnt"] if today_row else 0

        return {"total": total, "today": today}
    finally:
        conn.close()


def get_daily_chat(days: int = 14) -> List[dict]:
    conn = _get_conn()
    try:
        rows = conn.execute("""
            SELECT date(timestamp) AS day, COUNT(*) AS cnt
            FROM events
            WHERE event_type='chat' AND timestamp >= datetime('now','localtime',?)
            GROUP BY day ORDER BY day
        """, (f"-{days} days",)).fetchall()
        return [{"day": r["day"], "count": r["cnt"]} for r in rows]
    finally:
        conn.close()


# -- Feedback ------------------------------------------------------------------

def record_feedback(username: str, conversation_id: str, question: str,
                    answer_preview: str, feedback: str, route: str,
                    confidence: str, model: str, sources_count: int):
    conn = _get_conn()
    try:
        conn.execute(
            """INSERT INTO chat_feedback
               (username, conversation_id, question, answer_preview, feedback,
                route, confidence, model, sources_count)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (username, conversation_id, question, answer_preview[:200] if answer_preview else "",
             feedback, route, confidence, model, sources_count),
        )
        conn.commit()
    finally:
        conn.close()


def get_feedback_summary(days: int = 30) -> dict:
    conn = _get_conn()
    try:
        since = f"-{days} days"
        rows = conn.execute("""
            SELECT route, confidence, feedback, COUNT(*) AS cnt
            FROM chat_feedback
            WHERE timestamp >= datetime('now','localtime',?)
            GROUP BY route, confidence, feedback
        """, (since,)).fetchall()

        total = {"positive": 0, "negative": 0}
        by_route: dict = {}
        by_confidence: dict = {}

        for r in rows:
            fb = r["feedback"]
            cnt = r["cnt"]
            rt = r["route"] or "UNKNOWN"
            cf = r["confidence"] or "unknown"

            total[fb] = total.get(fb, 0) + cnt

            by_route.setdefault(rt, {"positive": 0, "negative": 0})
            by_route[rt][fb] = by_route[rt].get(fb, 0) + cnt

            by_confidence.setdefault(cf, {"positive": 0, "negative": 0})
            by_confidence[cf][fb] = by_confidence[cf].get(fb, 0) + cnt

        def _rate(d):
            s = d.get("positive", 0) + d.get("negative", 0)
            d["rate"] = round(d["positive"] / s * 100) if s else 0
            return d

        return {
            "total": _rate(total),
            "by_route": {k: _rate(v) for k, v in by_route.items()},
            "by_confidence": {k: _rate(v) for k, v in by_confidence.items()},
        }
    finally:
        conn.close()


def get_recent_negative(limit: int = 20) -> List[dict]:
    conn = _get_conn()
    try:
        rows = conn.execute("""
            SELECT timestamp, question, route, confidence, model, answer_preview
            FROM chat_feedback
            WHERE feedback='negative'
            ORDER BY timestamp DESC LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_daily_feedback(days: int = 14) -> List[dict]:
    conn = _get_conn()
    try:
        rows = conn.execute("""
            SELECT date(timestamp) AS day,
                   SUM(CASE WHEN feedback='positive' THEN 1 ELSE 0 END) AS positive,
                   SUM(CASE WHEN feedback='negative' THEN 1 ELSE 0 END) AS negative
            FROM chat_feedback
            WHERE timestamp >= datetime('now','localtime',?)
            GROUP BY day ORDER BY day
        """, (f"-{days} days",)).fetchall()
        return [{"day": r["day"], "positive": r["positive"], "negative": r["negative"]} for r in rows]
    finally:
        conn.close()


# -- Admin: reset / seed -------------------------------------------------------

def reset_all():
    conn = _get_conn()
    try:
        conn.execute("DELETE FROM events")
        conn.commit()
    finally:
        conn.close()
    _active_users.clear()


def seed_demo_data(days: int = 30):
    """Insert realistic demo data for the last N days."""
    conn = _get_conn()
    try:
        now = datetime.now()
        sample_pages = [
            "contents/samples/SWA_PMS/SWA_PMS.html",
            "contents/samples/FY1-DoD-FLEX-4/FY1-DoD-FLEX-4.html",
            "contents/samples/MyPaper/MyPaper_20251109_V2.8_Claude.html",
            "contents/dev-overview/introduction.html",
            "contents/about.html",
            "contents/home.html",
            "contents/samples/SWA_Sample_ENG/SWA_Sample_ENG.html",
            "contents/samples/SWA_Sample_KOR/SWA_Sample_KOR.html",
        ]
        sample_queries = [
            "KF-21", "보라매", "비행시험", "항전", "레이더",
            "추진", "무장", "시스템 설계", "체계개발", "FLEX",
            "PMS", "구조 시험", "인터페이스", "성능", "안전",
        ]

        rows = []
        for d in range(days, 0, -1):
            day = now - timedelta(days=d)
            day_str = day.strftime("%Y-%m-%d")
            # Visitors: 5-25 per day, weekdays more
            is_weekday = day.weekday() < 5
            n_visitors = random.randint(8, 25) if is_weekday else random.randint(3, 12)
            for v in range(n_visitors):
                ip = f"10.0.{random.randint(1,10)}.{random.randint(1,254)}"
                ts = f"{day_str} {random.randint(8,18):02d}:{random.randint(0,59):02d}:{random.randint(0,59):02d}"
                rows.append((ts, "visit", ip, None))
                # Each visitor views 1-5 pages
                for _ in range(random.randint(1, 5)):
                    page = random.choice(sample_pages)
                    rows.append((ts, "page_view", ip, json.dumps({"url": page})))

            # Searches: 3-15 per day
            for _ in range(random.randint(3, 15)):
                ip = f"10.0.{random.randint(1,10)}.{random.randint(1,254)}"
                ts = f"{day_str} {random.randint(8,18):02d}:{random.randint(0,59):02d}:{random.randint(0,59):02d}"
                query = random.choice(sample_queries)
                rows.append((ts, "search", ip, json.dumps({"query": query})))

            # Chats: 1-8 per day
            for _ in range(random.randint(1, 8)):
                ip = f"10.0.{random.randint(1,10)}.{random.randint(1,254)}"
                ts = f"{day_str} {random.randint(8,18):02d}:{random.randint(0,59):02d}:{random.randint(0,59):02d}"
                rows.append((ts, "chat", ip, None))

        conn.executemany(
            "INSERT INTO events (timestamp, event_type, ip, metadata) VALUES (?, ?, ?, ?)",
            rows,
        )
        conn.commit()
        return len(rows)
    finally:
        conn.close()
