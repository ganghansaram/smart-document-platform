"""
Analytics service -- SQLite event storage + in-memory active users
"""
import json
import logging
import os
import random
import sqlite3
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from fastapi import Request

import config

logger = logging.getLogger(__name__)

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
            username TEXT,
            subsystem TEXT,
            status TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
        CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);
        -- idx_events_subsystem 은 기존 DB 에 subsystem 컬럼이 없을 수 있어
        -- ALTER TABLE 마이그레이션 뒤 아래 루프에서 생성

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
    # 기존 DB 마이그레이션: 신규 컬럼 추가 (이미 존재하면 무시)
    for ddl in (
        "ALTER TABLE events ADD COLUMN username TEXT",
        "ALTER TABLE events ADD COLUMN subsystem TEXT",
        "ALTER TABLE events ADD COLUMN status TEXT",
        "CREATE INDEX IF NOT EXISTS idx_events_subsystem ON events(subsystem)",
    ):
        try:
            conn.execute(ddl)
            conn.commit()
        except Exception:
            pass
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

def record_heartbeat(ip: str, username: Optional[str] = None, subsystem: Optional[str] = None):
    now = time.time()
    key = (ip, subsystem or "")
    prev = _active_users.get(key)
    is_new_visit = prev is None or (now - prev["ts"]) > _ACTIVE_TIMEOUT
    _active_users[key] = {"ts": now, "username": username, "subsystem": subsystem, "ip": ip}
    # Record a visit event only on new sessions (first heartbeat or after timeout)
    if is_new_visit:
        record_event("visit", ip, None, username=username, subsystem=subsystem)


def record_event(event_type: str, ip: str, metadata: Optional[dict],
                 username: Optional[str] = None, *,
                 subsystem: Optional[str] = None, status: Optional[str] = None):
    conn = _get_conn()
    try:
        conn.execute(
            "INSERT INTO events (event_type, ip, metadata, username, subsystem, status) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (event_type, ip,
             json.dumps(metadata, ensure_ascii=False) if metadata else None,
             username, subsystem, status),
        )
        conn.commit()
    finally:
        conn.close()


# -- Query: Active users ------------------------------------------------------

def get_active_user_count() -> int:
    """현재 로그인 사용자 유니크 카운트 (username 기준, 익명·로그인페이지 체류 제외).
    Plan-43: 기존 IP 유니크 → username 유니크로 전환. 관리자가 "누가 지금
    쓰고 있나" 를 즉시 파악할 수 있도록 의미 명확화."""
    now = time.time()
    _cleanup_expired(now)
    usernames = {
        data.get("username")
        for (_ip, _sub), data in _active_users.items()
        if data.get("username")  # None·공백 제외
    }
    return len(usernames)


def get_active_ip_count() -> int:
    """IP 유니크 카운트 (익명·로그인페이지 체류 포함). 네트워크 수준 접근 수치."""
    now = time.time()
    _cleanup_expired(now)
    return len({ip for (ip, _sub) in _active_users.keys()})


def get_active_session_count(subsystem: Optional[str] = None) -> int:
    """(IP, subsystem) 유니크. 서브시스템 타일용."""
    now = time.time()
    _cleanup_expired(now)
    if subsystem is None:
        return len(_active_users)
    return sum(1 for (_ip, sub) in _active_users.keys() if sub == subsystem)


def get_active_user_list() -> List[dict]:
    """IP별 최신 활동 1건. 중복 서브시스템은 최근 타임스탬프 기준."""
    now = time.time()
    _cleanup_expired(now)
    by_ip: Dict[str, dict] = {}
    for (ip, sub), data in _active_users.items():
        cur = by_ip.get(ip)
        if cur is None or data["ts"] > cur["ts"]:
            by_ip[ip] = {**data, "subsystem": sub}
    result = []
    for ip, data in sorted(by_ip.items(), key=lambda x: x[1]["ts"], reverse=True):
        elapsed = int(now - data["ts"])
        result.append({
            "ip": ip,
            "elapsed_sec": elapsed,
            "username": data.get("username"),
            "subsystem": data.get("subsystem") or None,
        })
    return result


def _cleanup_expired(now: float):
    expired = [k for k, data in _active_users.items() if now - data["ts"] > _ACTIVE_TIMEOUT]
    for k in expired:
        del _active_users[k]


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


# -- Query: Subsystem stats (Plan-41) ------------------------------------------

_SUBSYSTEMS = ("explorer", "translator", "verify", "notebook")

# 각 서브시스템 타일에 노출할 핵심 지표 정의 (event_type → 라벨)
_SUBSYSTEM_METRICS = {
    "explorer":   [("page_view", "문서 열람"), ("chat", "챗봇")],
    "translator": [("translate", "번역"), ("summarize", "요약")],
    "verify":     [("compare", "비교"), ("upload", "업로드")],
    "notebook":   [("chat", "Q&A"), ("summarize", "요약")],
}


def get_subsystem_stats(days: int = 14) -> dict:
    """서브시스템별 오늘/14일 세션/지표/실패/추이 반환. 대시보드 타일용."""
    conn = _get_conn()
    try:
        result = {}
        for sub in _SUBSYSTEMS:
            # 오늘 세션 수 (IP 유니크)
            today_sessions = conn.execute(
                "SELECT COUNT(DISTINCT ip) AS cnt FROM events "
                "WHERE subsystem=? AND event_type='visit' "
                "AND date(timestamp)=date('now','localtime')",
                (sub,)
            ).fetchone()["cnt"] or 0

            # 지표 카운트 (오늘 기준)
            metrics = {}
            for event_type, label in _SUBSYSTEM_METRICS.get(sub, []):
                cnt = conn.execute(
                    "SELECT COUNT(*) AS cnt FROM events "
                    "WHERE subsystem=? AND event_type=? "
                    "AND date(timestamp)=date('now','localtime')",
                    (sub, event_type)
                ).fetchone()["cnt"] or 0
                metrics[event_type] = {"label": label, "count": cnt}

            # 오늘 실패 건수
            failures_today = conn.execute(
                "SELECT COUNT(*) AS cnt FROM events "
                "WHERE subsystem=? AND status='error' "
                "AND date(timestamp)=date('now','localtime')",
                (sub,)
            ).fetchone()["cnt"] or 0

            # 14일 추이 (세션 수 기준)
            trend = conn.execute("""
                SELECT date(timestamp) AS day, COUNT(DISTINCT ip) AS cnt
                FROM events
                WHERE subsystem=? AND event_type='visit'
                  AND timestamp >= datetime('now','localtime',?)
                GROUP BY day ORDER BY day
            """, (sub, f"-{days} days")).fetchall()

            result[sub] = {
                "today_sessions": today_sessions,
                "metrics": metrics,
                "failures_today": failures_today,
                "trend": [{"day": r["day"], "count": r["cnt"]} for r in trend],
            }
        return result
    finally:
        conn.close()


# -- Query: Top users (Plan-41) ------------------------------------------------

def get_top_users(days: int = 7, limit: int = 10) -> List[dict]:
    """활발한 사용자 TOP. users 테이블 name JOIN (Plan-42).
    name 이 없으면 username 단독 표시."""
    conn = _get_conn()
    try:
        # Events DB 와 Auth DB 가 동일 파일이면 JOIN, 다르면 name 없이 반환.
        try:
            conn.execute(f"ATTACH DATABASE '{config.AUTH_DB_PATH}' AS auth_db")
            rows = conn.execute("""
                SELECT e.username, u.name, COUNT(*) AS cnt
                FROM events e LEFT JOIN auth_db.users u ON u.username = e.username
                WHERE e.username IS NOT NULL
                  AND e.timestamp >= datetime('now','localtime',?)
                GROUP BY e.username ORDER BY cnt DESC LIMIT ?
            """, (f"-{days} days", limit)).fetchall()
            result = [
                {"username": r["username"], "name": r["name"], "count": r["cnt"]}
                for r in rows
            ]
            conn.execute("DETACH DATABASE auth_db")
            return result
        except Exception as e:
            # JOIN 실패 시 username 단독 폴백 (auth DB 경로 불일치·잠금·권한 등)
            logger.warning("top_users: auth_db ATTACH JOIN 실패, username 단독 폴백: %s", e)
            rows = conn.execute("""
                SELECT username, COUNT(*) AS cnt FROM events
                WHERE username IS NOT NULL
                  AND timestamp >= datetime('now','localtime',?)
                GROUP BY username ORDER BY cnt DESC LIMIT ?
            """, (f"-{days} days", limit)).fetchall()
            return [{"username": r["username"], "name": None, "count": r["cnt"]}
                    for r in rows]
    finally:
        conn.close()


# -- Query: Recent failures (Plan-41) ------------------------------------------

def get_recent_failures(limit: int = 20) -> List[dict]:
    """최근 실패 이벤트 (status='error'). 대시보드 실패 피드용."""
    conn = _get_conn()
    try:
        rows = conn.execute("""
            SELECT timestamp, event_type, subsystem, username, metadata
            FROM events WHERE status='error'
            ORDER BY timestamp DESC LIMIT ?
        """, (limit,)).fetchall()
        return [{
            "timestamp": r["timestamp"],
            "event_type": r["event_type"],
            "subsystem": r["subsystem"],
            "username": r["username"],
            "metadata": json.loads(r["metadata"]) if r["metadata"] else None,
        } for r in rows]
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
    """Insert realistic demo data for the last N days across all subsystems."""
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
        # 샘플 사용자 — 활동 빈도 차등(testbot·emp001 주력, 나머지 조연)으로
        # 대시보드 "활발한 사용자 TOP" 위젯에 분포감 있는 결과 형성
        sample_users = [
            ("testbot", 0.30),
            ("emp001", 0.25),
            ("emp002", 0.18),
            ("emp003", 0.12),
            ("emp004", 0.08),
            ("emp005", 0.07),
        ]
        sample_docs = ["doc-abc", "doc-def", "doc-ghi", "doc-jkl", "doc-mno"]
        sample_translate_engines = ["pmt", "pmt", "pmt", "web"]  # 3:1 비율
        sample_compare_files = [
            ("spec_v1.pdf", "spec_v2.pdf"),
            ("rfp_original.docx", "rfp_revised.docx"),
            ("design_rev1.pdf", "design_rev2.pdf"),
        ]
        error_endpoints = [
            ("/api/translator/translate/xyz/page/5", "translator"),
            ("/api/compare/similarity", "verify"),
            ("/api/chat", "explorer"),
        ]

        def _pick_user():
            r = random.random()
            cum = 0.0
            for u, w in sample_users:
                cum += w
                if r <= cum:
                    return u
            return sample_users[-1][0]

        def _ts(day_str):
            return f"{day_str} {random.randint(8,18):02d}:{random.randint(0,59):02d}:{random.randint(0,59):02d}"

        def _ip():
            return f"10.0.{random.randint(1,10)}.{random.randint(1,254)}"

        rows = []
        # days-1 ~ 0 — 오늘(d=0) 포함, 대시보드 타일 "오늘 세션" 미리보기용
        for d in range(days - 1, -1, -1):
            day = now - timedelta(days=d)
            day_str = day.strftime("%Y-%m-%d")
            is_weekday = day.weekday() < 5

            # ── Explorer 방문 / page_view ──
            n_visitors = random.randint(8, 25) if is_weekday else random.randint(3, 12)
            for v in range(n_visitors):
                ip = _ip()
                user = _pick_user()
                ts = _ts(day_str)
                rows.append((ts, "visit", ip, None, user, "explorer", None))
                for _ in range(random.randint(1, 5)):
                    page = random.choice(sample_pages)
                    rows.append((ts, "page_view", ip,
                                 json.dumps({"url": page}), user, "explorer", None))

            # ── Explorer 검색 ──
            for _ in range(random.randint(3, 15) if is_weekday else random.randint(1, 6)):
                rows.append((_ts(day_str), "search", _ip(),
                             json.dumps({"query": random.choice(sample_queries)}),
                             _pick_user(), "explorer", None))

            # ── Explorer 챗봇 ──
            for _ in range(random.randint(1, 8) if is_weekday else random.randint(0, 3)):
                rows.append((_ts(day_str), "chat", _ip(), None,
                             _pick_user(), "explorer", None))

            # ── Translator visits (heartbeat 모의) ──
            n_trans_visits = random.randint(3, 8) if is_weekday else random.randint(1, 4)
            for _ in range(n_trans_visits):
                rows.append((_ts(day_str), "visit", _ip(), None,
                             _pick_user(), "translator", None))

            # ── Translator upload + translate + summarize ──
            n_uploads = random.randint(1, 3) if is_weekday else random.randint(0, 1)
            for _ in range(n_uploads):
                rows.append((_ts(day_str), "upload", _ip(),
                             json.dumps({"filename": f"paper_{random.randint(1,99)}.pdf",
                                         "size": random.randint(500_000, 20_000_000),
                                         "ext": "pdf"}),
                             _pick_user(), "translator", "ok"))
            n_translates = random.randint(3, 10) if is_weekday else random.randint(1, 4)
            for _ in range(n_translates):
                engine = random.choice(sample_translate_engines)
                status = "error" if random.random() < 0.08 else "started"
                page = random.randint(1, 30)
                rows.append((_ts(day_str), "translate", _ip(),
                             json.dumps({"doc_id": random.choice(sample_docs),
                                         "pages": [page], "engine": engine}),
                             _pick_user(), "translator", status))
            for _ in range(random.randint(0, 3)):
                rows.append((_ts(day_str), "summarize", _ip(),
                             json.dumps({"doc_id": random.choice(sample_docs),
                                         "mode": "generate"}),
                             _pick_user(), "translator", "started"))

            # ── Verify visits (heartbeat 모의) ──
            n_verify_visits = random.randint(1, 4) if is_weekday else random.randint(0, 2)
            for _ in range(n_verify_visits):
                rows.append((_ts(day_str), "visit", _ip(), None,
                             _pick_user(), "verify", None))

            # ── Verify upload + compare ──
            for _ in range(random.randint(0, 2) if is_weekday else 0):
                rows.append((_ts(day_str), "upload", _ip(),
                             json.dumps({"filename": f"doc_{random.randint(1,99)}.docx",
                                         "size": random.randint(200_000, 10_000_000),
                                         "ext": "docx"}),
                             _pick_user(), "verify", "ok"))
            n_compares = random.randint(2, 6) if is_weekday else random.randint(0, 2)
            for _ in range(n_compares):
                target, ref = random.choice(sample_compare_files)
                mode = random.choice(["similarity", "similarity", "validate"])
                status = "error" if random.random() < 0.05 else "ok"
                meta = {"mode": mode}
                if mode == "similarity":
                    meta.update({
                        "target_len": random.randint(2000, 20000),
                        "reference_len": random.randint(2000, 20000),
                        "score": round(random.uniform(0.55, 0.95), 3),
                    })
                else:
                    meta.update({
                        "paragraph_count": random.randint(30, 200),
                        "issue_count": random.randint(0, 15),
                    })
                rows.append((_ts(day_str), "compare", _ip(),
                             json.dumps(meta), _pick_user(), "verify", status))

            # ── Notebook visits (heartbeat 모의) ──
            n_nb_visits = random.randint(1, 3) if is_weekday else random.randint(0, 1)
            for _ in range(n_nb_visits):
                rows.append((_ts(day_str), "visit", _ip(), None,
                             _pick_user(), "notebook", None))

            # ── Notebook Q&A ──
            for _ in range(random.randint(0, 5) if is_weekday else random.randint(0, 2)):
                rows.append((_ts(day_str), "chat", _ip(),
                             json.dumps({"doc_id": random.choice(sample_docs)}),
                             _pick_user(), "notebook", "started"))

            # ── 산발 5xx 에러 (주 1~3건) ──
            if random.random() < 0.15:
                endpoint, sub = random.choice(error_endpoints)
                rows.append((_ts(day_str), "error", _ip(),
                             json.dumps({"endpoint": endpoint, "status": 500,
                                         "exception": random.choice(
                                             ["TimeoutError", "ValueError", "RuntimeError"])}),
                             _pick_user(), sub, "error"))

        conn.executemany(
            "INSERT INTO events (timestamp, event_type, ip, metadata, "
            "username, subsystem, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
            rows,
        )
        conn.commit()
        return len(rows)
    finally:
        conn.close()
