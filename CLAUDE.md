# Smart Document Platform

## 핵심 제약
- **Vanilla JS only** — 프레임워크/라이브러리 금지 (폐쇄망 운용 환경)
- **모놀리식 HTML** — 각 서브시스템은 단일 HTML 파일 (inline JS/CSS)
- **빌드 시스템 없음** — 번들러, 트랜스파일러 사용하지 않음

## 실행 환경
```bash
# 백엔드 (FastAPI)
cd backend && python main.py          # http://localhost:8000

# 프론트엔드 (정적 서버)
python -m http.server 8080            # http://localhost:8080
```

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
- diff 색상 → `var(--diff-added)`, `var(--diff-deleted)` 등 사용

### 공통 컴포넌트 클래스 (components.css)
| 용도 | 클래스 | 변형 |
|------|--------|------|
| 버튼 | `.btn` | `.btn-primary`, `.btn-secondary`, `.btn-ghost`, `.btn-danger`, `.btn-icon`, `.btn-icon-lg`, `.btn-sm` |
| 입력 | `.form-input` | `.form-textarea`, `.form-select`, `.form-group`, `.form-input-sm`, `.form-select-sm`, `.form-input-lg` |
| 배지 | `.badge` | `.badge-success`, `.badge-warning`, `.badge-error`, `.badge-info` |
| 스피너 | `.spinner` | `.spinner-sm`, `.spinner-lg` |
| 리사이즈 | `.resize-handle` | — |

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

## 테스트 계정
- ID: `testbot` / PW: `test1234`
