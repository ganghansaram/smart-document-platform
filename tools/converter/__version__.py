# -*- coding: utf-8 -*-
"""DOCX→HTML 변환기 버전 (Plan-37 이후)."""

__version__ = "1.6.0"
"""
버전 이력:
  1.6.0  — Plan-73: 캡션 감지 2계층 분리. 표시 캡션(class 만, 프론트 JS 폴백과
           동일 기준)을 신설해 구분자 없는 "표 1 시스템 구성" 등 표기 편차를
           흡수. 본문 오탐은 조사 배제("표 1을 보면"·"그림 3과 같이")와 길이
           가드로 2겹 차단. 참조 캡션(id·본문 링크)은 무변경 — 판정이 엄격해야
           중복 id·오탐 링크가 안 생긴다. 표시용 CSS 는 캡션↔대상 인접 규칙을
           이미지 문단 양방향으로 확장.
  1.5.0  — standalone(exe) 웹북 안전화: CLI 전처리 기본 OFF(+Word COM 타임아웃
           가드) + 출력에 표시용 CSS 내장(.docx-content 래퍼+스코프 style).
           엔진(converter.py) 로직 무변경 — 변경은 standalone 래퍼/spec 한정.
  1.4.0  — Plan-37: 엔진 SSOT + cascade heading + 전처리 어댑터 체인 +
           provenance meta + 시맨틱 품질 게이트
  ≤1.3.x — Plan-37 이전 (legacy 2단계 heading, standalone 분기 병행)
"""
