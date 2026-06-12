# Plan-32: 관리자 설정 메뉴 재구조화

## 목표
관리자 설정을 "기능 유형별"(AI, 콘텐츠, 검색...) → **"서브시스템별"**(공통, Explorer, Notebook, Verify)로 재편하여 설정의 자기완결성과 탐색 효율을 높인다.

## 배경
- Plan-30에서 탭 통폐합(11→8), 항목 정리(63→29), AI 모델 전역화 완료
- 그러나 모델 오버라이드가 3곳 분산, Explorer 전용 설정이 공통과 혼재
- `TRANSLATOR_AI_SUMMARY_MODEL`이 settings_service 미등록 (관리 사각지대)
- 오픈 전이므로 기존 사용자 경험 호환 부담 없음

## 현행 → 목표 매핑

### 좌측 사이드바 구조

```
현행 (8개)                        목표 (6개)
─────────────                    ─────────────
관리                              관리
  계정 관리                         계정 관리
  대시보드                          대시보드
플랫폼 설정                       공통
  일반                            Explorer
  AI 연결                         Notebook
  콘텐츠                          Verify
  검색 / 챗봇
  번역
  문서 검증
```

### 설정 항목 재배치

```
공통                                       ← 단일 페이지 (탭 없음)
  ├─ AI 연결
  │   ├─ Ollama URL                       (restart)
  │   └─ 플랫폼 AI 모델                    (restart)
  └─ 보안
      ├─ 열람 로그인 필수                   (restart)
      └─ 로그인 세션 만료 (시간)             (restart)

Explorer
  ├─ [콘텐츠] 탭
  │   ├─ 표시
  │   │   ├─ 사이트 타이틀              ← 공통에서 이동
  │   │   └─ 테이블 스타일
  │   ├─ 업로드
  │   │   ├─ 업로드 기능 활성화
  │   │   ├─ 최대 파일 크기 (MB)
  │   │   ├─ 업로드 후 검색 인덱스 자동 갱신
  │   │   └─ 업로드 후 벡터 인덱스 자동 갱신
  │   ├─ 에디터                            ← 공통에서 이동
  │   │   ├─ 에디터 활성화
  │   │   ├─ 저장 시 백업 생성
  │   │   └─ 자동 저장 간격
  │   └─ 메뉴 관리                         (custom)
  ├─ [검색] 탭
  │   └─ 검색
  │       ├─ 검색 방식
  │       ├─ 리랭커 사용
  │       ├─ 키워드 비중 (하이브리드)
  │       └─ 최소 벡터 유사도
  └─ [챗봇] 탭
      └─ 챗봇
          ├─ AI 챗봇 표시                  ← AI연결에서 이동
          ├─ 시스템 프롬프트
          ├─ 참조 문서 수                  ← "최대 검색 결과 수" 라벨 변경
          ├─ 쿼리 재작성                   ← 검색에서 이동 (RAG 전용)
          ├─ 최대 컨텍스트 길이
          ├─ 최대 대화 턴 수               ← 일반에서 이동
          └─ 유휴 세션 만료 (분)           ← 일반에서 이동

Notebook
  └─ [번역] 탭
      ├─ 모델
      │   └─ Notebook 전용 모델            ← 번역+요약 통합, 라벨 변경
      ├─ PDF 번역
      │   ├─ 테이블 텍스트 번역
      │   ├─ OCR 우회
      │   ├─ PDF 시스템 프롬프트
      │   ├─ 리치텍스트 번역 비활성화
      │   └─ 호환성 강화
      ├─ 웹뷰 번역
      │   ├─ 표 추출 모드
      │   ├─ 수식 추출 모드
      │   └─ 이미지 해상도 (DPI)
      ├─ AI 기능
      │   ├─ 번역 완료 시 자동 요약        ← 웹뷰에서 이동
      │   ├─ 선택 번역 프롬프트
      │   └─ 선택 요약 프롬프트
      └─ 성능
          ├─ 동시 번역 수
          └─ 페이지 타임아웃 (초)

Verify
  ├─ [유사도 검사] 탭                      ← 핵심 기능, 첫 탭으로 이동
  │   ├─ 분류 임계값
  │   │   ├─ 동일 판정 기준 (L1)
  │   │   └─ 유사 판정 하한 (L3)
  │   └─ 판정 라벨 경계
  │       ├─ 양호/보통 경계 (%)
  │       └─ 보통/주의 경계 (%)
  ├─ [AI 비교] 탭
  │   └─ AI 의미 분류
  │       ├─ AI 분석 활성화
  │       ├─ 시스템 프롬프트
  │       ├─ Verify 전용 모델              ← 라벨 변경
  │       └─ 온도
  └─ [규칙 관리] 탭                        (custom)
```

### 항목 이동 요약

| 항목 | 이전 위치 | 이후 위치 | 이유 |
|------|-----------|-----------|------|
| 사이트 타이틀 | 일반 > 사이트 | Explorer > 콘텐츠 > 표시 | Explorer 헤더 전용 설정 |
| 에디터 3항목 | 일반 > 에디터/고급 | Explorer > 콘텐츠 > 에디터 | Explorer 전용 (Notebook 미참조) |
| AI 챗봇 표시 | AI 연결 > 기능 | Explorer > 챗봇 | Explorer 전용 기능 |
| 참조 문서 수 | 검색/챗봇 > 검색 | Explorer > 챗봇 | RAG 전용, 라벨 변경 |
| 쿼리 재작성 | 검색/챗봇 > 검색 | Explorer > 챗봇 | RAG 전용 기능 |
| 대화 턴/유휴 세션 | 일반 > 고급 | Explorer > 챗봇 | Explorer 챗봇 세션 설정 |
| 컨텍스트 길이 | 검색/챗봇 > 고급 | Explorer > 챗봇 | RAG 전용 |
| 번역 완료 시 자동 요약 | Notebook 번역 > 웹뷰 | Notebook 번역 > AI 기능 | 요약은 번역 하위가 아닌 독립 기능 |
| PDF 프롬프트 등 3건 | Notebook 번역 > 고급 | Notebook 번역 > PDF 번역 | 해당 기능 섹션에 평탄 배치 |
| 이미지 DPI | Notebook 번역 > 고급 | Notebook 번역 > 웹뷰 번역 | 웹뷰 추출 옵션 |
| 타임아웃 | Notebook 번역 > 고급 | Notebook 번역 > 성능 | 성능 관련 |
| 선택 번역/요약 프롬프트 | Notebook 번역 > 고급 | Notebook 번역 > AI 기능 | AI 기능 섹션으로 통합 |
| Verify 전용 모델/온도 | 문서 검증 > AI비교 > 고급 | Verify > AI 비교 > AI 의미 분류 | 평탄 배치 |

### 모델 오버라이드 통합

| 현행 | 목표 | 변경 |
|------|------|------|
| `TRANSLATOR_TRANSLATION_MODEL` (번역 전용) | `TRANSLATOR_MODEL` (Notebook 전용) | 변수 리네임, 번역+요약 공용 |
| `TRANSLATOR_AI_SUMMARY_MODEL` (요약 전용) | 제거 | 위에 통합 |
| `COMPARE_AI_MODEL` (비교 전용) | 유지 | 라벨만 "Verify 전용 모델"로 변경 |

## 작업 범위

### Phase 1: 스키마 재구성 (프론트엔드)
- `admin-settings.js`의 `SETTINGS_SCHEMA` 재배치
  - `group` 값 변경: '플랫폼 설정' → '공통' / 'Explorer' / 'Notebook' / 'Verify'
  - `id`/`label` 조정, 탭/섹션/필드 이동
- 렌더링 로직 변경 없음 (기존 group→탭→섹션 구조 재사용)

### Phase 2: 모델 오버라이드 통합 (백엔드)
- `config.py`: `TRANSLATOR_AI_SUMMARY_MODEL` 제거, `TRANSLATOR_TRANSLATION_MODEL` → `TRANSLATOR_MODEL` 리네임
- `settings_service.py`: `translator.translation_model` 키 유지, `apply_to_config` 매핑 갱신
- `ai_summary.py`: `TRANSLATOR_AI_SUMMARY_MODEL` → `TRANSLATOR_MODEL` 참조로 변경
- `translator_service.py`: `TRANSLATOR_TRANSLATION_MODEL` → `TRANSLATOR_MODEL` 참조로 변경
- `settings_service.py`: `get_public_settings()`에 `notebook_model` 노출 (Notebook 전용 모델 or 플랫폼 기본 모델 폴백)

### Phase 3: Notebook 기본 모델 자동 선택
- `translator.js`의 `loadModels()`에서 `/api/settings/public`의 `notebook_model`을 `defaultModel`로 사용
- 현행: `defaultModel = ''` 하드코딩 → 목록 첫 번째 모델이 선택됨
- 목표: 관리자가 설정한 모델이 기본 선택, 사용자가 필요 시 드롭다운에서 변경 가능

### Phase 4: 챗봇 모델명 표시 (이미 완료)
- `settings_service.py`: `get_public_settings()`에 `ai_model_name` 노출 — 완료
- `app.js`: `loadRuntimeSettings()`에서 모델명 DOM 업데이트 — 완료
- `ai-chat.js`: 하드코딩 제거, config.js 폴백 — 완료

### Phase 5: 문서 갱신
- `docs/` 관련 문서 반영 (설정 변수명 변경분)

## 영향 범위
- `js/admin-settings.js` — SETTINGS_SCHEMA 재배치 (주 작업)
- `js/translator.js` — `loadModels()` 기본 모델 연결
- `backend/config.py` — 변수 리네임 1건, 제거 1건
- `backend/services/settings_service.py` — 매핑 갱신, `get_public_settings()` 확장
- `backend/services/ai_summary.py` — 모델 참조 변경
- `backend/services/translator_service.py` — 모델 참조 변경
- 기존 `settings.json` 호환: `translator.translation_model` 키 유지로 마이그레이션 불필요

## 미포함 (의도적 제외)
- 렌더링 로직/UI 레이아웃 변경 — 기존 탭+섹션 렌더러 그대로 사용
- settings.json 키 구조 변경 — 프론트 스키마만 재배치, 저장 키는 유지
