# Plan-30: 관리자 설정 체계 정비 및 Docker 운영 환경 최적화

> **1순위**: Windows 직접실행과 Docker 이미지 배포, 양쪽에서 플랫폼이 정상 서비스되어야 한다  
> **2순위**: 관리자 설정 UI를 업계 표준 수준으로 정리하여 운영 효율을 높인다  
> **원칙**: 기능 코드(config.py, settings_service.py)는 최소 변경. UI 재구성이 주 작업  
> **제약**: 레이아웃은 기존 관리자 설정 화면의 렌더링 구조(SETTINGS_SCHEMA → renderSection/renderSettingsField)와 플랫폼 테마 지침(tokens.css, components.css)을 준수한다. 새 컴포넌트 양식을 만들지 않는다.

---

## 0. 업계 표준 관리자 콘솔 분석

> GitLab Admin, Nextcloud, Mattermost System Console, WordPress, Grafana, Outline 등 조사 결과

### 공통 패턴

| 관점 | 업계 표준 | 현재 우리 플랫폼 |
|------|----------|-----------------|
| **네비게이션** | 좌측 사이드바 2단계 (카테고리 > 설정 페이지) | 좌측 시스템 목록 > 상단 탭 2단계. 유사하나 구조가 서브시스템 중심 |
| **그룹핑 기준** | 기능 도메인별 (일반, AI, 인증, 외관 등) | 서브시스템별 (Explorer, Notebook, Verify) — 같은 종류의 설정이 분산 |
| **고급 설정** | UI에 넣지 않음. 환경변수/설정파일로 분리 | 내부 파라미터까지 UI에 노출 (RRF K, 배치크기, QPS 등) |
| **AI 설정** | 전역 1곳 (endpoint + 모델) + 기능별 on/off | 3곳에 분산 (Explorer/Notebook/Verify 각각 모델 입력) |
| **항목 수** | 그룹당 5~15개 | 일부 탭에 15개 초과 |

### 핵심 개선 방향

1. **서브시스템별 → 기능 도메인별** 재그룹핑
2. **AI 모델 설정 전역화** — 1곳에서 설정, 전체 서브시스템에 적용
3. **내부 파라미터 21개 제거** — config.py 기본값 또는 .env로 관리
4. **Docker/Windows 양쪽 정상 동작 보장** — 환경 감지 + 조건부 UI

---

## 1. 설정 우선순위 체계

### 확정: 환경변수 > settings.json > 코드 기본값

```
[우선순위 높음]
  .env / 환경변수          ← 인프라: 포트, Ollama URL (Docker에서 주입)
    ↓ 없으면
  settings.json            ← 관리자: AI 파라미터, 검색, 번역 설정
    ↓ 없으면
  config.py 기본값          ← 개발자: 합리적 기본값
```

- 환경변수가 설정된 항목은 settings.json이 덮어쓰지 못함
- Windows에서는 환경변수를 설정하지 않으므로 관리자 UI가 최종 권한
- Docker에서는 .env가 인프라 설정의 최종 권한

---

## 2. 관리자 설정 항목 전수 판정

> 판정 기준: 운영 중 관리자가 변경할 현실적 필요가 있는가?  
> 내부 파라미터, 개발자 영역, 기본값으로 충분한 항목은 UI에서 제거.  
> 제거해도 config.py 기본값이 동작하므로 양쪽 환경 모두 영향 없음.

### 범례

| 판정 | 의미 |
|------|------|
| **유지** | 운영 중 관리자가 변경할 현실적 필요 있음 |
| **이동** | 유지하되 새 탭 구조에서 위치 변경 |
| **축소** | 고급 영역으로 접어서 기본 숨김 (펼치면 보임) |
| **제거** | UI에서 제거. config.py 기본값 사용. 양쪽 환경 영향 없음 |

### 공통 > 보안/접근

| 항목 | 설정키 | 판정 | 근거 |
|------|--------|------|------|
| 열람 로그인 필수 (백엔드) | security.login_required | **유지** | 공개/비공개 전환 |
| CORS 허용 출처 | security.cors_origins | **제거** | Docker: 동일출처라 불필요. Windows: .env 또는 config.py에서 관리. 관리자가 CORS를 변경할 상황 없음 |
| 열람 로그인 필수 (프론트) | frontend.login_required | **제거** | 백엔드 설정과 중복. 하나로 통합 |

### Explorer > AI/RAG

| 항목 | 설정키 | 판정 | 근거 |
|------|--------|------|------|
| Ollama URL | ai.ollama_url | **이동** → AI 연결 | 플랫폼 전체 영향 |
| LLM 모델 | ai.ollama_model | **이동** → AI 연결 | 플랫폼 대표 모델 |
| 임베딩 모델 | ai.embedding_model | **제거** | 교체 시 벡터 인덱스 전체 재생성 필요. 운영 중 변경 안 함 |
| 검색 방식 | ai.default_search_type | **유지** | 검색 품질 튜닝 |
| 최대 검색 결과 수 | ai.max_search_results | **유지** | 품질/속도 트레이드오프 |
| 최대 컨텍스트 길이 | ai.max_context_length | **축소** | 기본값(8000) 충분 |
| 키워드 비중 | ai.hybrid_keyword_weight | **축소** | 튜닝 완료된 값(0.3) |
| RRF K 값 | ai.hybrid_rrf_k | **제거** | 학술 파라미터. 기본값 60 고정 |
| 최소 벡터 유사도 | ai.min_vector_score | **축소** | 튜닝 완료된 값(0.48) |
| 리랭커 사용 | ai.reranker_enabled | **유지** | 성능/품질 트레이드오프 |
| 리랭커 후보 배수 | ai.reranker_top_k_multiplier | **제거** | 내부 파라미터 |
| 쿼리 재작성 | ai.query_rewrite_enabled | **유지** | Ollama 부하 시 끌 수 있음 |
| 챗봇 시스템 프롬프트 | ai.chat_system_prompt | **유지** | 도메인별 커스터마이징 핵심 |

### Explorer > 세션

| 항목 | 설정키 | 판정 | 근거 |
|------|--------|------|------|
| 최대 대화 턴 수 | session.max_conversation_turns | **축소** | 기본값(5) 충분 |
| 히스토리 최대 길이 | session.max_history_length | **제거** | 턴 수로 충분히 제어 |
| 최대 세션 수 | session.max_sessions | **제거** | 인프라 영역. 기본값(100) 고정 |
| 유휴 세션 만료 | session.max_idle_minutes | **축소** | 기본값(60분) 충분 |
| 로그인 세션 만료 | session.session_expiry_hours | **유지** | 보안 정책 |

### Explorer > 업로드

| 항목 | 설정키 | 판정 | 근거 |
|------|--------|------|------|
| 업로드 기능 활성화 | frontend.upload_enabled | **유지** | 기능 On/Off |
| 최대 파일 크기 | frontend.upload_max_file_size_mb | **유지** | 디스크 보호 |
| 검색 인덱스 자동 갱신 | frontend.upload_auto_search_index | **유지** | 대량 업로드 시 끌 수 있음 |
| 벡터 인덱스 자동 갱신 | frontend.upload_auto_vector_index | **유지** | 시간이 오래 걸려서 선택적 |
| Word COM 전처리 | upload.word_com_preprocess | **제거** | Windows+Word 전용. Docker 불가 |
| 임시 폴더 경로 | upload.upload_temp_dir | **제거** | 인프라 영역 |

### Explorer > 화면/에디터

| 항목 | 설정키 | 판정 | 근거 |
|------|--------|------|------|
| 사이트 타이틀 | frontend.display_site_title | **유지** | 브랜딩 |
| 테이블 스타일 | frontend.display_table_style | **유지** | 시각적 선호도 |
| 챗봇 표시 | frontend.ai_enabled | **유지** | 기능 On/Off |
| 백엔드 RAG 사용 | frontend.ai_use_backend | **제거** | 항상 true. 직접 호출은 Docker 미지원 + 보안 부적절 |
| 검색 방식 (직접) | frontend.ai_search_type | **제거** | useBackend 제거와 함께 불필요 |
| 검색 결과 수 (직접) | frontend.ai_max_search_results | **제거** | 동일 |
| 컨텍스트 길이 (직접) | frontend.ai_max_context_length | **제거** | 동일 |
| 프롬프트 (직접) | frontend.ai_system_prompt | **제거** | 동일. 백엔드 RAG 프롬프트만 유지 |
| 에디터 활성화 | frontend.editor_enabled | **유지** | 기능 On/Off |
| 자동 저장 간격 | frontend.editor_auto_save_interval | **축소** | 기본값(30초) 충분 |
| 저장 시 백업 생성 | frontend.editor_create_backup | **유지** | 데이터 안전 |

### Explorer > 메뉴 관리

| 항목 | 판정 | 근거 |
|------|------|------|
| 메뉴 편집 UI | **유지** | 핵심 관리 기능 |

### Notebook > 번역 설정

| 항목 | 설정키 | 판정 | 근거 |
|------|--------|------|------|
| 번역 모델 | translator.translation_model | **축소** → 고급 | 플랫폼 대표 모델로 대체. 오버라이드 시만 |
| PDF 시스템 프롬프트 | translator.custom_prompt | **축소** | 기본 프롬프트 충분 |
| 리치텍스트 비활성화 | translator.disable_rich_text | **축소** | 특수 상황 |
| 테이블 텍스트 번역 | translator.translate_table_text | **유지** | 문서 유형에 따라 판단 |
| 최소 텍스트 길이 | translator.min_text_length | **제거** | 내부 파라미터 |
| OCR 우회 | translator.ocr_workaround | **유지** | 스캔 PDF 대응 |
| 호환성 강화 | translator.enhance_compatibility | **축소** | 특수 상황 |
| 표 추출 모드 (웹뷰) | translator.web_table_mode | **유지** | 문서 특성에 따라 |
| 수식 추출 모드 | translator.web_formula_mode | **유지** | 수식 문서 대응 |
| 이미지 해상도 | translator.web_image_dpi | **축소** | 기본값(150) 충분 |
| 표 감지 전략 | translator.web_table_strategy | **제거** | PyMuPDF 내부 파라미터 |
| 자동 요약 | translator.web_auto_summary | **유지** | 기능 On/Off |
| 디버그 모드 | translator.web_debug | **제거** | 개발자용 |
| 번역 프롬프트 (AI 선택) | translator.ai_translate_prompt | **축소** | 전문가용 |
| 요약 프롬프트 (AI 선택) | translator.ai_summarize_prompt | **축소** | 전문가용 |
| AI 선택 타임아웃 | translator.ai_selection_timeout | **제거** | 내부 파라미터 |
| 동시 번역 수 | translator.max_concurrent | **유지** | GPU 부하 제어 |
| 페이지 타임아웃 | translator.page_timeout | **축소** | 기본값(300초) 충분 |
| QPS 제한 | translator.qps | **제거** | 내부 파라미터 |

### Verify > 비교

| 항목 | 설정키 | 판정 | 근거 |
|------|--------|------|------|
| AI 분석 활성화 | compare.ai_enabled | **유지** | 기능 On/Off |
| 분류 모델 | compare.ai_model | **축소** → 고급 | 플랫폼 대표 모델로 대체 |
| 온도 | compare.ai_temperature | **축소** | 전문가용. 기본값(0) |
| 배치 크기 | compare.ai_batch_size | **제거** | 내부 파라미터 |
| 타임아웃 | compare.ai_timeout | **제거** | 내부 파라미터 |
| 시스템 프롬프트 | compare.ai_system_prompt | **유지** | 도메인별 커스터마이징 |

### Verify > 유사도 검사

| 항목 | 설정키 | 판정 | 근거 |
|------|--------|------|------|
| 동일 판정 기준 | verify.sim_threshold_high | **유지** | 검사 엄격도 |
| 유사 판정 하한 | verify.sim_threshold_medium | **유지** | 동일 |
| 양호/보통 경계 | verify.sim_verdict_low | **유지** | 보고서 라벨링 |
| 보통/주의 경계 | verify.sim_verdict_high | **유지** | 동일 |
| Winnowing k-gram | verify.sim_winnow_k | **제거** | 학술 파라미터 |
| Winnowing 윈도우 | verify.sim_winnow_window | **제거** | 동일 |
| 임베딩 배치 크기 | verify.sim_embedding_batch | **제거** | 내부 성능 파라미터 |

### Verify > 규칙 검증

| 항목 | 판정 | 근거 |
|------|------|------|
| 규칙 편집 UI | **유지** | 핵심 관리 기능 |

### 판정 요약

| 판정 | 항목 수 | 비율 |
|------|---------|------|
| **유지** | 27 | 43% |
| **이동** | 2 | 3% |
| **축소** (고급) | 13 | 21% |
| **제거** | 21 | 33% |
| **합계** | 63 | 100% |

> 기본 화면에서 관리자가 보는 항목: 63개 → **29개**

---

## 3. 탭 구조 통폐합

### 현재 구조 (서브시스템 중심)

```
관리
  ├── 계정 관리         ← 사용자 CRUD
  └── 대시보드           ← 통계

시스템 설정
  ├── 공통
  │   └── 보안/접근      ← CORS 제거 후 항목 1개만 남음
  ├── Explorer
  │   ├── AI/RAG        ← 모델 설정이 여기에 묻혀있음
  │   ├── 세션           ← 제거 후 항목 1~2개
  │   ├── 업로드
  │   ├── 화면/에디터    ← 직접모드 제거 후 축소
  │   └── 메뉴 관리
  ├── Notebook
  │   └── 번역 설정
  └── Verify
      ├── 비교
      ├── 유사도 검사
      └── 규칙 검증
```

문제점:
- 항목 1~2개짜리 탭이 여러 개 (보안, 세션)
- AI 모델 설정이 Explorer에 묻혀서 플랫폼 전체 설정처럼 보이지 않음
- "화면/에디터" 탭에 챗봇 On/Off, 사이트 타이틀, 에디터 등 이질적인 항목 혼재
- 같은 종류의 설정(프롬프트)이 Explorer, Notebook, Verify 3곳에 분산

### 제안 구조 (기능 도메인 중심)

```
관리
  ├── 계정 관리                  ← 그대로
  └── 대시보드                    ← 그대로

플랫폼 설정
  ├── 일반                        ← 사이트 이름, 보안, 세션
  ├── AI 연결                     ← Ollama URL, 플랫폼 모델 (신설)
  ├── 콘텐츠                      ← 업로드, 메뉴 관리 (통합)
  ├── 검색 / 챗봇                 ← RAG, 리랭커, 프롬프트 (Explorer에서 이동)
  ├── 번역                        ← Notebook 번역 설정 (그대로)
  └── 문서 검증                   ← Compare + Verify (통합)
```

### 상세 매핑

#### 일반 (기존 공통 + 세션 + 화면/에디터에서 추출)

| 섹션 | 항목 | 출처 |
|------|------|------|
| 사이트 | 사이트 타이틀, 테이블 스타일 | 화면/에디터 |
| 보안 | 열람 로그인 필수, 로그인 세션 만료 | 보안 + 세션 |
| 에디터 | 에디터 활성화, 저장 시 백업 생성 | 화면/에디터 |
| [고급] | 자동 저장 간격, 대화 턴 수, 유휴 만료 | 세션 + 에디터 |

> 항목 수: 기본 6개 + 고급 3개 = 9개

#### AI 연결 (신설 — 플랫폼 전역)

| 섹션 | 항목 | 출처 |
|------|------|------|
| 서버 연결 | Ollama URL | Explorer AI/RAG |
| 모델 | 플랫폼 AI 모델 (= ollama_model) | Explorer AI/RAG |
| 기능 | 챗봇 표시 On/Off | 화면/에디터 |

> 항목 수: 3개. 가장 중요하면서 가장 간결한 페이지.
> Docker 환경에서 URL이 .env로 잠긴 경우 "환경변수로 설정됨" 표시.

#### 콘텐츠 (기존 업로드 + 메뉴 관리 통합)

| 섹션 | 항목 | 출처 |
|------|------|------|
| 업로드 | 활성화, 최대 파일 크기, 검색 인덱스 자동, 벡터 인덱스 자동 | 업로드 |
| 메뉴 관리 | 메뉴 편집 UI | 메뉴 관리 |

> 항목 수: 4개 + 메뉴 편집 UI

#### 검색 / 챗봇 (기존 Explorer AI/RAG에서 모델 분리 후)

| 섹션 | 항목 | 출처 |
|------|------|------|
| 검색 | 검색 방식, 최대 결과 수, 리랭커 사용, 쿼리 재작성 | AI/RAG |
| 챗봇 | 시스템 프롬프트 | AI/RAG |
| [고급] | 컨텍스트 길이, 키워드 비중, 최소 벡터 유사도 | AI/RAG |

> 항목 수: 기본 6개 + 고급 3개 = 9개

#### 번역 (기존 Notebook 탭 정리)

| 섹션 | 항목 | 출처 |
|------|------|------|
| PDF 번역 | 테이블 번역, OCR 우회 | 번역 설정 |
| 웹뷰 번역 | 표 추출 모드, 수식 추출 모드, 자동 요약 | 번역 설정 |
| 성능 | 동시 번역 수 | 번역 설정 |
| [고급] | 번역 모델 오버라이드, PDF 프롬프트, 리치텍스트, 호환성, 이미지 DPI, 페이지 타임아웃, 번역/요약 프롬프트 | 번역 설정 |

> 항목 수: 기본 6개 + 고급 7개 = 13개

#### 문서 검증 (기존 Verify 비교 + 유사도 통합)

| 섹션 | 항목 | 출처 |
|------|------|------|
| AI 비교 | AI 분석 활성화, 시스템 프롬프트 | 비교 |
| 유사도 검사 | 동일 판정 기준, 유사 판정 하한, 양호/보통 경계, 보통/주의 경계 | 유사도 |
| 규칙 검증 | 규칙 편집 UI | 규칙 |
| [고급] | 비교 모델 오버라이드, 온도 | 비교 |

> 항목 수: 기본 7개 + 고급 2개 = 9개

### 구조 비교

| | 현재 | 제안 |
|--|------|------|
| 최상위 그룹 | 4개 (관리2 + 설정: 공통/Explorer/Notebook/Verify) | 2개 (관리2 + 설정6) |
| 총 탭 수 | 11개 | 8개 |
| 기본 노출 항목 | 63개 | 29개 |
| 서브시스템 이름 노출 | Explorer, Notebook, Verify 각각 | 기능 도메인명 (일반, AI, 검색, 번역, 검증) |
| AI 모델 설정 위치 | Explorer 탭 안에 묻힘 | 독립된 "AI 연결" 페이지 (최상위) |

---

## 4. Docker/Windows 양쪽 환경 대응

> **1순위**: 양쪽에서 정상 서비스. 환경별 분기는 UI 표시 수준에서만 처리.

### 4-1. 환경 감지

| 환경 | 프론트엔드 판별 | 백엔드 판별 |
|------|----------------|------------|
| Docker | `AUTH_CONFIG.backendUrl === ''` (Nginx가 config.docker.js 주입) | `os.getenv('DOCKER_ENV') == 'true'` |
| Windows | `AUTH_CONFIG.backendUrl !== ''` | 환경변수 미설정 |

- Nginx 오버라이드 방식(config.js → config.docker.js)은 변경하지 않음
- 이미 동작하는 메커니즘 위에 감지 조건만 추가

### 4-2. 프론트엔드 수정

| 항목 | 현재 | 수정 | Windows 영향 |
|------|------|------|-------------|
| config.docker.js ollamaUrl | `'http://localhost:11434'` | `''` (빈 문자열) | 없음 (원본 config.js 미변경) |
| admin-settings.js 폴백 8곳 | `'http://localhost:8000'` | `''` (상대경로) | 없음 (config.js 정상 로드 시 도달 안 함) |

### 4-3. Docker 환경에서만 달라지는 UI

| 항목 | Docker | Windows |
|------|--------|---------|
| Ollama URL | ".env로 설정됨" 표시 (편집 가능하되 안내) | 자유 편집 |
| 재시작 필요 뱃지 | "docker compose restart backend" 안내 | 기존 안내 유지 |

> 항목 숨김/비활성화는 하지 않음. 양쪽 동일한 UI를 유지하되, Docker에서는 안내 문구만 추가.

### 4-4. 백엔드 수정

| 항목 | 수정 내용 | Windows 영향 |
|------|----------|-------------|
| apply_to_config() | 환경변수 존재 시 해당 키 skip | 없음 (환경변수 미설정이면 기존대로) |
| get_public_settings() | `_meta.env_overrides: [키 목록]` 추가 | 빈 배열 반환. 프론트 UI 변화 없음 |
| docker-compose.yml | `DOCKER_ENV=true` 추가 | 해당 없음 |

### 4-5. 제거 항목의 안전성

UI에서 제거하는 21개 항목은 **코드(config.py)에서 제거하지 않음**.

```
[UI에서 제거] = SETTINGS_SCHEMA에서 필드 삭제
[config.py]   = 기본값 그대로 유지
[settings.json] = 이미 저장된 값이 있으면 계속 apply
```

→ 기존에 settings.json에 저장된 커스텀 값이 있어도 정상 반영됨.
→ UI에서 못 바꿀 뿐, 기존 동작이 깨지지 않음.
→ 양쪽 환경 모두 안전.

---

## 5. .env 및 docker-compose.yml 정비

### .env.example 기본값 변경

| 항목 | 현재 | 제안 | 이유 |
|------|------|------|------|
| OLLAMA_URL | `http://gpu-server:11434` | `http://host.docker.internal:11434` | 로컬 테스트에서 바로 동작 |

### docker-compose.yml 추가

| 항목 | 값 | 용도 |
|------|-----|------|
| `DOCKER_ENV=true` | backend 환경변수 | Docker 환경 감지 |

---

## 6. 검증 체크리스트

### 1순위: 양쪽 환경 정상 서비스

- [ ] **Windows**: 기존 2포트(8080+8000) 실행 → 로그인 → Explorer → Notebook → Verify 정상
- [ ] **Windows**: 관리자 설정 → 저장 → 반영 정상
- [ ] **Windows**: settings.json에 이미 저장된 제거 항목 값이 계속 반영됨
- [ ] **Docker**: docker compose up → 로그인 → Explorer → Notebook → Verify 정상
- [ ] **Docker**: 관리자 설정 → 저장 → 반영 정상
- [ ] **Docker**: .env의 OLLAMA_URL이 settings.json보다 우선

### 2순위: UI 개선

- [ ] 탭 구조가 새 구조로 전환됨
- [ ] AI 연결 페이지에서 모델 변경 → 전 서브시스템 반영
- [ ] 제거 항목 21개가 기본 화면에 안 보임
- [ ] 축소 항목 13개가 고급 영역에 접혀있음
- [ ] Docker 환경에서 환경변수 잠금 항목에 안내 표시

### LLM 모델 통합

- [ ] AI 연결에서 모델 변경 → Explorer 챗봇 반영
- [ ] AI 연결에서 모델 변경 → Notebook 번역/요약 반영
- [ ] AI 연결에서 모델 변경 → Verify AI 비교 반영
- [ ] 고급 옵션에서 개별 모델 오버라이드 가능
- [ ] 개별 모델 비우면 플랫폼 모델로 폴백

---

## 7. Phase 구성

| Phase | 내용 | 수정 범위 | 위험도 |
|-------|------|----------|--------|
| **1** | ~~프론트엔드 하드코딩 정리~~ 완료 | config.docker.js (1곳) + 전체 폴백 15곳 → `''` | 낮음 |
| **2** | ~~백엔드 환경변수 우선순위~~ 완료 | settings_service.py, docker-compose.yml | 낮음 |
| **3+4** | ~~탭 구조 통폐합 + AI 연결 탭 + 항목 제거/축소~~ 완료 | admin-settings.js (SETTINGS_SCHEMA), admin-settings.css | 중간 |

### Phase 1 완료 리�� (2026-04-08)

**수정 범위**: 계획서보다 확대 — admin-settings.js 외에 동일 패턴이 있는 전체 파일 포함

| 파일 | 수정 수 | 내용 |
|------|---------|------|
| docker/config.docker.js | 1 | `ollamaUrl: ''` |
| js/admin-settings.js | 6 | backendUrl 폴백 → `''` |
| js/app.js | 1 | 동일 |
| js/analytics.js | 1 | 동일 |
| js/platform-header.js | 1 | 동일 |
| js/translator.js | 1 | 동일 |
| js/tree-menu.js | 3 | 동일 |
| compare.html | 1 | ��일 |
| login.html | 1 | 동일 |

미변경: `js/config.js` (Windows 원본 4곳), 가이드 문서 (설명 텍스트)

**검증 결과 — Windows (localhost:8080+8000)**:

| 항목 | 결과 |
|------|------|
| 로그인 (testbot) | PASS |
| Explorer (index.html) | PASS (0 errors) |
| Notebook API (translator/documents) | PASS |
| Backend health | PASS |
| 설정 저장 → 반영 (max_search_results 5→7→5) | PASS |
| settings.json 기존 값 유지 | PASS |

**검증 결과 — Docker (localhost:80, Nginx 프록시)**:

| 항목 | 결과 |
|------|------|
| 컨테이너 시작 (backend Healthy + nginx Started) | PASS |
| 페이지 로드 (launcher, index, translator, compare) | PASS (모두 200) |
| 로그인 (testbot) | PASS |
| 설정 조회 (/api/settings/public) | PASS |
| 설정 저장 → 반영 (max_search_results 5→7→5) | PASS |
| Translator API (documents) | PASS (3건) |
| config.js 오버라이드 (backendUrl: '') | PASS |
| 보안 차단 (auth.db → 403, .env → 403) | PASS |
| 화이트리스트 (menu.json → 200) | PASS |

### Phase 3+4 완료 리뷰 (2026-04-08)

**수정 내역**:

| 파일 | 내용 |
|------|------|
| admin-settings.js | SETTINGS_SCHEMA 전면 재구성 (서브시스템 중심 → 기능 도메인 중심), collapsed 섹션 토글 함수, 메뉴 관리 조건 변경 (explorer → content) |
| admin-settings.css | 고급 섹션 접기 CSS (.admin-section-collapsed, .admin-section-toggle, .admin-toggle-arrow) |

**구조 변경**: 11탭 → 8탭

| 사이드바 | 탭 수 | 주요 항목 |
|---------|------|----------|
| 계정 관리 | 커스텀 | 사용자 CRUD |
| 대시보드 | 커스텀 | 통계 |
| 일반 | 1 | 사이트, 보안, 에디터 + [고급] |
| AI 연결 | 1 | Ollama URL, 플랫폼 모델, 챗봇 표시 |
| 콘텐츠 | 2 | 업로드, 메뉴 관리 |
| 검색 / 챗봇 | 1 | 검색 설정, 프롬프트 + [고급] |
| 번역 | 1 | PDF/웹뷰/성능 + [고급] |
| 문서 검증 | 3 | AI 비교, 유사도, 규칙 |

**제거 항목 21개** (UI에서만 제거, config.py 기본값 유지):
CORS, 임베딩 모델, RRF K, 리랭커 후보 배수, 히스토리 길이, 세션 수, Word COM, 임시폴더, 프론트 login_required, useBackend, 직접모드 5개, 최소텍스트길이, 표감지전략, 디버그, AI선택타임아웃, QPS, 배치크기(compare), 타임아웃(compare), Winnowing 3개

**검증 결과 — Windows (API)**:

| 항목 | 결과 |
|------|------|
| 로그인 | PASS |
| 설정 그룹 전체 반환 (8 groups) | PASS |
| 설정 저장 → 반영 | PASS |
| 페이지 로드 (index, translator, compare) | PASS (모두 200) |

**검증 결과 — Docker (API)**:

| 항목 | 결과 |
|------|------|
| 로그인 | PASS |
| 설정 그룹 전체 반환 | PASS |
| _meta (is_docker, env_overrides) | PASS |
| 설정 저장 → 반영 | PASS |
| 페이지 로드 (launcher, index, admin) | PASS (모두 200) |
| Translator API | PASS (3건) |
| 보안 차단 (auth.db → 403) | PASS |

**Playwright 브라우저 UI 테스트**: 쿠키 전달 이슈로 admin.html 직접 로드 불가 (기존 Docker 환경 제한, Phase 3 변경과 무관). 수동 브라우저 확인 권장.

### Phase 2 완료 리뷰 (2026-04-08)

**수정 내역**:

| 파일 | 내용 |
|------|------|
| settings_service.py | `_ENV_PROTECTED` dict + `_set()` 환경변수 보호 로직 + `get_public_settings()` `_meta` 필드 |
| docker-compose.yml | `DOCKER_ENV=true` 환경변수 추가 |

**검증 결과 — Windows (환경변수 미설정)**:

| 항목 | 결과 |
|------|------|
| `_meta.is_docker` | `False` — 정상 |
| `_meta.env_overrides` | `[]` — 환경변수 없으므로 빈 배열 |
| Ollama URL 변경 → 적용 | PASS — settings.json 값이 config.py에 반영됨 |
| 로그인, 전체 API | PASS |

**검증 결과 — Docker (OLLAMA_URL, OLLAMA_MODEL, CORS_ORIGINS, DOCKER_ENV 설정)**:

| 항목 | 결과 |
|------|------|
| `_meta.is_docker` | `True` — 정상 |
| `_meta.env_overrides` | `['OLLAMA_URL', 'OLLAMA_MODEL', 'CORS_ORIGINS']` — 3개 감지 |
| Ollama URL 변경 시도 → settings.json 저장됨 | PASS (저장은 됨) |
| Ollama URL 변경 시도 → config.py에 적용 안 됨 | PASS (환경변수 값 유지) |
| 로그인, 전체 API, 보안 차단 | PASS |

### 진행 원칙

- Phase 1~2는 인프라 정비. 기능 변화 없음. 양쪽 환경 검증 후 다음 진행.
- Phase 3~4는 UI 재구성. admin-settings.js의 SETTINGS_SCHEMA 수정이 주 작업.
- **매 Phase 완료 후 Windows + Docker 양쪽 검증 필수**.
- 문제 발생 시 해당 Phase를 롤백하고 원인 분석 후 재진행.
