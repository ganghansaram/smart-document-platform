# Smart Document Platform

## 핵심 제약
- **Vanilla JS only** — 프레임워크/라이브러리 금지 (폐쇄망 운용 환경)
- **모놀리식 HTML** — 각 서브시스템은 단일 HTML 파일 (inline JS/CSS)
- **빌드 시스템 없음** — 번들러, 트랜스파일러 사용하지 않음

## 배포 환경 (3종)
| 환경 | 구성 | 용도 |
|------|------|------|
| **개발 PC (집)** | Windows + WSL2 + Docker Desktop | 개발·테스트, `localhost:80` |
| **회사 리눅스 VM** | Ubuntu 24.04 + Docker | 주 서비스, tar 이미지 배포 |
| **회사 Windows PC** | 톰캣 + Python 백엔드 (Docker 없음) | 대안 서비스, 프로젝트 디렉토리 통째 복사 |

- 코드는 Docker 전용 기능에 의존하지 않아야 함 (Windows 직접 실행도 지원)
- 프론트엔드는 정적 파일 — 톰캣/Nginx/http.server 어디서든 서빙 가능
- 백엔드는 `python main.py`로 직접 실행 가능 (Docker 없이도)

## 실행 방법
```bash
# ── Docker (개발 PC / 회사 리눅스) ──
docker compose up -d                  # http://localhost:80
# override가 소스 bind mount → 코드 수정 즉시 반영
# 프론트엔드: Ctrl+F5, 백엔드: docker compose restart backend
# 개발 PC Docker→Ollama 접근 불가 (WSL 제한) → AI 기능 테스트 시 아래 방식 사용

# ── 직접 실행 (회사 Windows / AI 기능 테스트) ──
cd backend && python main.py          # http://localhost:8000
python -m http.server 8080            # http://localhost:8080
```

## Docker 운영
- 가이드: `docs/03-DOCKER-OPERATIONS.md`
- 개발 (override 자동 적용, bind mount): `docker compose up -d`
- 프로덕션 (override 배제): `docker compose -f docker-compose.yml up -d`
- 환경 변수: `.env`에서 `CORS_ORIGINS`, `OLLAMA_URL`, `PORT` 등 관리
- 배포 스크립트: `deploy.sh`, `patch-apply.sh` — `COMPOSE_FILE` 고정과 경로는 Plan-31 Phase 1 방어선 (임의 수정 금지, `memory/feedback_docker_prod_scripts.md` 참조)
- 검증 시 HTTP 200만으론 부족 — `Last-Modified`·액세스 로그·컨테이너 내부 curl 교차 확인 (`memory/feedback_docker_verification.md`)

## 서브시스템
| 시스템 | 진입점 | 설명 |
|--------|--------|------|
| 플랫폼 | `launcher.html`, `login.html` | 런처, 인증, 공통 헤더 |
| Explorer | `index.html` | 웹북 탐색기, RAG 검색, AI 채팅 |
| Translator | `translator.html` | 논문 번역, PDF 듀얼 뷰어 |
| Compare | `compare.html` | 문서 비교, 규칙 검증 |

## 스타일 규칙 (디자인 시스템)

### CSS 로드 순서
모든 HTML 페이지는 아래 순서로 공통 CSS를 로드해야 한다:
```html
<link rel="stylesheet" href="css/tokens.css">      <!-- 1. 변수 -->
<link rel="stylesheet" href="css/scrollbar.css">    <!-- 2. 스크롤바 (필요 시) -->
<link rel="stylesheet" href="css/toast.css">        <!-- 3. 토스트 (필요 시) -->
<link rel="stylesheet" href="css/components.css">   <!-- 4. 공통 컴포넌트 (필요 시) -->
<link rel="stylesheet" href="css/modal.css">        <!-- 5. 모달 (필요 시) -->
<link rel="stylesheet" href="css/platform-header.css"> <!-- 6. 헤더 -->
<!-- 이후 페이지 전용 CSS -->
```

### 악센트 컬러 — 플랫폼 통일 블루
- 모든 서브시스템이 동일한 악센트 컬러를 사용한다 (서브시스템별 오버라이드 금지)
- Light `#2c5282` / Dark `#63a0e0` — `tokens.css`에 정의
- 새 페이지에서 `--active-color`를 인라인 `<style>`로 오버라이드하지 않는다
- 다크모드에서도 `#58a6ff` 등 하드코딩 대신 `var(--active-color)` 사용

### 하드코딩 금지
- 색상 → `var(--active-color)`, `var(--color-error)` 등 tokens.css 변수 사용
- 간격 → `var(--space-sm)` ~ `var(--space-2xl)` 사용 권장
- 둥글기 → `var(--radius-sm)` ~ `var(--radius-xl)` 사용 권장
- 트랜지션 → `var(--transition-fast)` ~ `var(--transition-slow)` 사용 권장
- diff 색상 → `var(--diff-added)`, `var(--diff-deleted)` 등 사용 (배경/텍스트/테두리/단어 토큰 구분, 다크모드 자동 전환)

### 공통 컴포넌트 클래스 (components.css)
| 용도 | 클래스 | 변형 |
|------|--------|------|
| 버튼 | `.btn` | `.btn-primary`, `.btn-secondary`, `.btn-ghost`, `.btn-danger`, `.btn-icon`, `.btn-icon-sm`, `.btn-icon-lg`, `.btn-sm` |
| 입력 | `.form-input` | `.form-textarea`, `.form-select`, `.form-group`, `.form-input-sm`, `.form-select-sm`, `.form-input-lg` |
| 배지 | `.badge` | `.badge-success`, `.badge-warning`, `.badge-error`, `.badge-info` |
| 스피너 | `.spinner` | `.spinner-sm`, `.spinner-lg` |
| 리사이즈 | `.resize-handle` | — |
| 슬라이더 | `.form-range-wrap` > `.form-range` | `.form-range-value` — 현재값 배지 표시 |
| 툴팁 | `.tooltip-icon` | `.tooltip-bottom` — `data-tooltip="설명"` 속성으로 내용 지정 |
| 진입 카드 | `.entry-card` | 시스템 홈 진입 타일·허브 카드 공통 스킨(평상시 elevation+호버 들림). Author `.au-tile`·Verify `.verify-hub-card` 가 확장(레이아웃은 각자) |

### 모달 (modal.css)
새 모달은 `.modal-overlay` + `.modal-box` + `.modal-header` / `.modal-body` / `.modal-footer` 조합.

### 새 공통 패턴 추가 시
1. `css/components.css` 또는 해당 공통 CSS에 클래스 정의
2. 다크 모드 변형 포함
3. 위 컴포넌트 테이블 업데이트

## 작업 원칙
1. **의견 먼저, 구현은 승인 후** — 비자명한 작업은 먼저 논의
2. **기존 코드 읽고 나서 수정** — 패턴/컨벤션 파악 후 작업
3. **과도한 엔지니어링 금지** — 요청된 범위만 구현
4. **커밋은 요청 시에만** — 자동 커밋 금지, 규칙은 `.claude/skills/commit` 참조

## 계획서(Workbench) 관리
- **인덱스 SSOT**: `workbench/plans/README.md` — 전 계획의 상태·위치 단일 출처. 계획 위치를 찾을 땐 여기부터.
- **상태 = 폴더**: 활성 `plans/*.md` · 완료 `plans/done/` · 보류 `plans/icebox/` (옛 `done-` 접두어 폐기, 폴더로 대체)
- **완료 처리 (계획 종료 시 항상 수행)**:
  1. 헤더 `상태:` → `✅ 완료 (요약)` 갱신
  2. `git mv NN-제목.md done/NN-제목.md`
  3. `plans/README.md` 의 해당 행을 활성 → 완료 섹션으로 이동
  4. 외부 문서(`docs/` 등)가 옛 경로 참조 시 `plans/done/NN-…` 로 정정
- 보류 전환도 동일 (`git mv … icebox/` + README 이동). 상세는 README "디렉토리 규약" 참조.

## 유사도 분류 체계 (Plan-45 v3, Copyleaks 모방)

### 카테고리 (4) — 사용자 UI에 노출되는 분류 단위
- **동일** (identical) · **거의 동일** (near_copy) · **의역** (paraphrased, translation 통합) · **약한 유사** (low_similarity, 점수 제외 참고용)
- 추가 제외 영역: **자동 제외** (boilerplate + 활성 exclusion_reason) · **수동 제외** (사용자 ⓧ 판정)

### 알고리즘 유형 (6) — 백엔드 분류 키
- `identical` / `near_copy` / `paraphrase` / `translation` / `low_sim` / `boilerplate`
- 카드에는 SSOT `labels.*.ko` 라벨로 노출 (translation 도 "의역"으로 표시)

### 점수 공식 (가중치 없음)
```
유사율 = (동일 + 거의 동일 + 의역) / (전체 문장 - 제외 문장) × 100
```

### 규칙
1. 라벨은 `data/help/similarity-help.json` (SSOT) 경유만 허용 — 하드코딩 금지
2. 축약 금지 — 유사도 카드 라벨로 "일치"·"번역" 사용 불가 (v3 어휘: 동일·의역)
3. Plan-38 옛 그룹 어휘 (표절 의심·참고 가능·제외 영역·4그룹) 사용 금지
4. 카테고리 판정은 `compare.html` 의 `resolveCategory(match, settings)` 단일 함수만 사용
5. 필터 = 가시성 (점수 무영향) · 설정 = 점수 재계산 · 수동 제외 = 가시성 + 점수 재계산
6. 자동/수동 제외 카드는 메인 리스트에 노출 금지 — `<details class="sim-exclusion-panel">` 만 사용

### 자동 검증
- `bash tests/sim_label_consistency.sh` — grep 기반 SSOT 우회·옛 어휘·옛 공식 검사
- pre-commit hook 또는 CI 등록 권장

## 테스트 계정
- ID: `testbot` / PW: `test1234`
