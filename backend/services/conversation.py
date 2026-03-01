"""
인메모리 대화 세션 저장소
"""
import uuid
import time
import threading
from typing import Dict, List, Optional

import config


class ConversationSession:
    __slots__ = ("id", "history", "created_at", "last_active")

    def __init__(self, session_id: str):
        self.id = session_id
        self.history: List[dict] = []   # [{"role": "user"|"assistant", "content": str}, ...]
        self.created_at = time.time()
        self.last_active = time.time()

    MAX_HISTORY_MESSAGES = 50  # 최대 25턴 (user+assistant 쌍)

    def add_message(self, role: str, content: str):
        self.history.append({"role": role, "content": content})
        self.last_active = time.time()
        # 히스토리 상한 초과 시 오래된 메시지 제거
        if len(self.history) > self.MAX_HISTORY_MESSAGES:
            self.history = self.history[-self.MAX_HISTORY_MESSAGES:]

    def get_history(self, max_turns: int = 0) -> List[dict]:
        """최근 max_turns 쌍(user+assistant)을 반환. 0이면 전체."""
        if max_turns <= 0:
            return list(self.history)
        # 각 쌍은 2개 메시지 (user + assistant)
        limit = max_turns * 2
        return list(self.history[-limit:])


class ConversationStore:
    """스레드 안전 인메모리 세션 저장소 (LRU 퇴거)"""

    def __init__(self):
        self._sessions: Dict[str, ConversationSession] = {}
        self._lock = threading.Lock()

    def create_session(self) -> ConversationSession:
        session_id = uuid.uuid4().hex[:16]
        session = ConversationSession(session_id)
        with self._lock:
            self._evict_if_needed()
            self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[ConversationSession]:
        with self._lock:
            session = self._sessions.get(session_id)
            if session:
                session.last_active = time.time()
            return session

    def _evict_if_needed(self):
        """유휴 세션 정리 + LRU 퇴거"""
        now = time.time()
        max_idle = config.MAX_IDLE_MINUTES * 60

        # 1) 유휴 세션 삭제
        expired = [
            sid for sid, s in self._sessions.items()
            if now - s.last_active > max_idle
        ]
        for sid in expired:
            del self._sessions[sid]

        # 2) 여전히 초과면 LRU 퇴거
        while len(self._sessions) >= config.MAX_SESSIONS:
            oldest = min(self._sessions, key=lambda k: self._sessions[k].last_active)
            del self._sessions[oldest]


# 싱글턴 인스턴스
store = ConversationStore()
