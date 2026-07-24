# -*- coding: utf-8 -*-
"""DOCX→HTML 변환기 버전 (Plan-37 이후)."""

__version__ = "1.5.0"
"""
버전 이력:
  1.5.0  — standalone(exe) 웹북 안전화: CLI 전처리 기본 OFF(+Word COM 타임아웃
           가드) + 출력에 표시용 CSS 내장(.docx-content 래퍼+스코프 style).
           엔진(converter.py) 로직 무변경 — 변경은 standalone 래퍼/spec 한정.
  1.4.0  — Plan-37: 엔진 SSOT + cascade heading + 전처리 어댑터 체인 +
           provenance meta + 시맨틱 품질 게이트
  ≤1.3.x — Plan-37 이전 (legacy 2단계 heading, standalone 분기 병행)
"""
