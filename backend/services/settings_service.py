"""
관리자 설정 서비스 — settings.json CRUD + 런타임 config 적용
"""
import json
import os
from pathlib import Path
from typing import Any

import config as _config

_SETTINGS_PATH = Path(_config.AUTH_DB_PATH).parent / "settings.json"

# ── 기본값 (config.py / config.js 기준) ──────────────────────────────────────

DEFAULT_SETTINGS: dict = {
    "ai": {
        "ollama_url": "http://localhost:11434",
        "ollama_model": "gemma3:4b",
        "embedding_model": "bge-m3",
        "max_search_results": 5,
        "max_context_length": 8000,
        "default_search_type": "hybrid",
        "hybrid_keyword_weight": 0.3,
        "hybrid_rrf_k": 60,
        "min_vector_score": 0.48,
        "reranker_enabled": True,
        "reranker_top_k_multiplier": 3,
        "query_rewrite_enabled": True,
    },
    "session": {
        "max_conversation_turns": 5,
        "max_history_length": 2000,
        "max_sessions": 100,
        "max_idle_minutes": 60,
        "session_expiry_hours": 24,
    },
    "security": {
        "login_required": True,
        "cors_origins": ["http://localhost:8080", "http://127.0.0.1:8080"],
    },
    "translator": {
        "translation_model": "",
    },
    "upload": {
        "word_com_preprocess": False,
        "upload_temp_dir": None,
    },
    "frontend": {
        "ai_enabled": True,
        "ai_use_backend": True,
        "ai_search_type": "hybrid",
        "ai_max_search_results": 5,
        "ai_max_context_length": 8000,
        "ai_system_prompt": (
            "당신은 KF-21 전투기 기술 문서 전문 어시스턴트입니다. "
            "제공된 참고 문서만을 기반으로 답변합니다.\n\n"
            "[핵심 규칙]\n"
            "1. 오직 제공된 문서 내용만 사용하여 답변합니다\n"
            "2. 문서에 없는 내용은 절대 추측하지 않습니다\n"
            "3. 정보가 없으면 \"제공된 문서에서 해당 정보를 찾지 못했습니다\"라고 답변합니다\n\n"
            "[답변 방식]\n"
            "- 핵심 내용을 먼저 간결하게 제시합니다\n"
            "- 필요시 불릿 포인트나 번호 목록으로 구조화합니다\n"
            "- 기술 용어는 문서에 표기된 그대로 사용합니다\n"
            "- 답변 끝에 참고한 문서 제목을 명시합니다\n\n"
            "[언어]\n한국어로 답변합니다."
        ),
        "editor_enabled": True,
        "editor_auto_save_interval": 30000,
        "editor_create_backup": True,
        "upload_enabled": True,
        "upload_auto_search_index": False,
        "upload_auto_vector_index": False,
        "upload_max_file_size_mb": 500,
        "display_table_style": "bordered",
        "display_site_title": "WebBook",
        "login_required": True,
    },
}

# ── 항목별 재시작 필요 여부 ────────────────────────────────────────────────────

# 서버 재시작 없이 즉시 반영 가능한 항목 경로 (group.key 형식)
_NO_RESTART = {
    "ai.max_search_results", "ai.max_context_length", "ai.default_search_type",
    "ai.hybrid_keyword_weight", "ai.hybrid_rrf_k", "ai.min_vector_score",
    "ai.reranker_enabled", "ai.reranker_top_k_multiplier", "ai.query_rewrite_enabled",
    "session.max_conversation_turns", "session.max_history_length",
    "session.max_sessions", "session.max_idle_minutes",
    "upload.word_com_preprocess", "upload.upload_temp_dir",
    "translator.translation_model",
    "frontend",  # prefix match
}
# 나머지(ollama_url, ollama_model, embedding_model, session_expiry_hours,
# security.login_required, security.cors_origins) = 재시작 필요


def _deep_merge(base: dict, override: dict) -> dict:
    """base에 override를 재귀 병합"""
    result = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(result.get(k), dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


# ── CRUD ──────────────────────────────────────────────────────────────────────

def load_settings() -> dict:
    """settings.json 읽기. 없으면 DEFAULT_SETTINGS 반환. DEFAULT와 병합."""
    if not _SETTINGS_PATH.exists():
        return _deep_merge({}, DEFAULT_SETTINGS)
    try:
        raw = json.loads(_SETTINGS_PATH.read_text(encoding="utf-8"))
        return _deep_merge(DEFAULT_SETTINGS, raw)
    except Exception:
        return _deep_merge({}, DEFAULT_SETTINGS)


def save_settings(data: dict) -> None:
    """data를 settings.json에 저장 (원자적: 임시파일 → rename)."""
    tmp = _SETTINGS_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(_SETTINGS_PATH)


def reset_settings() -> dict:
    """settings.json 삭제 → 기본값 반환."""
    if _SETTINGS_PATH.exists():
        _SETTINGS_PATH.unlink()
    return _deep_merge({}, DEFAULT_SETTINGS)


def get_public_settings() -> dict:
    """프론트엔드 공개용: frontend 그룹만 반환."""
    s = load_settings()
    return s.get("frontend", DEFAULT_SETTINGS["frontend"])


# ── 런타임 config 적용 ────────────────────────────────────────────────────────

def apply_to_config(settings: dict) -> list[str]:
    """
    settings dict를 config 모듈 변수에 즉시 반영.
    재시작이 필요한 항목 목록 반환.
    """
    restart_needed = []

    ai = settings.get("ai", {})
    _set(ai, "ollama_url",            "OLLAMA_URL",                restart_needed)
    _set(ai, "ollama_model",          "OLLAMA_MODEL",              restart_needed)
    _set(ai, "embedding_model",       "EMBEDDING_MODEL",           restart_needed)
    _set(ai, "max_search_results",    "MAX_SEARCH_RESULTS",        restart_needed, immediate=True)
    _set(ai, "max_context_length",    "MAX_CONTEXT_LENGTH",        restart_needed, immediate=True)
    _set(ai, "default_search_type",   "DEFAULT_SEARCH_TYPE",       restart_needed, immediate=True)
    _set(ai, "hybrid_keyword_weight", "HYBRID_KEYWORD_WEIGHT",     restart_needed, immediate=True)
    _set(ai, "hybrid_rrf_k",         "HYBRID_RRF_K",              restart_needed, immediate=True)
    _set(ai, "min_vector_score",      "MIN_VECTOR_SCORE",          restart_needed, immediate=True)
    _set(ai, "reranker_enabled",      "RERANKER_ENABLED",          restart_needed, immediate=True)
    _set(ai, "reranker_top_k_multiplier", "RERANKER_TOP_K_MULTIPLIER", restart_needed, immediate=True)
    _set(ai, "query_rewrite_enabled", "QUERY_REWRITE_ENABLED",     restart_needed, immediate=True)

    sess = settings.get("session", {})
    _set(sess, "max_conversation_turns", "MAX_CONVERSATION_TURNS", restart_needed, immediate=True)
    _set(sess, "max_history_length",     "MAX_HISTORY_LENGTH",     restart_needed, immediate=True)
    _set(sess, "max_sessions",           "MAX_SESSIONS",           restart_needed, immediate=True)
    _set(sess, "max_idle_minutes",       "MAX_IDLE_MINUTES",       restart_needed, immediate=True)
    _set(sess, "session_expiry_hours",   "SESSION_EXPIRY_HOURS",   restart_needed)

    sec = settings.get("security", {})
    _set(sec, "login_required", "LOGIN_REQUIRED", restart_needed)
    _set(sec, "cors_origins",   "CORS_ORIGINS",   restart_needed)

    rdr = settings.get("translator", {})
    _set(rdr, "translation_model", "TRANSLATOR_TRANSLATION_MODEL", restart_needed, immediate=True)

    upl = settings.get("upload", {})
    _set(upl, "word_com_preprocess", "WORD_COM_PREPROCESS", restart_needed, immediate=True)
    _set(upl, "upload_temp_dir",     "UPLOAD_TEMP_DIR",     restart_needed, immediate=True)

    return restart_needed


def _set(group: dict, key: str, config_attr: str, restart_list: list,
         immediate: bool = False) -> None:
    if key not in group:
        return
    val = group[key]
    setattr(_config, config_attr, val)
    if not immediate:
        restart_list.append(config_attr)


# ── 시작 시 자동 적용 ─────────────────────────────────────────────────────────

def apply_settings_on_startup() -> None:
    """서버 시작 시 settings.json → config 모듈 적용."""
    try:
        settings = load_settings()
        apply_to_config(settings)
    except Exception:
        pass  # 실패해도 기본값으로 동작
