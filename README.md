# Smart Document Platform

에어갭(폐쇄망) 환경에서 사용 가능한 AI 기반 기술문서 웹 플랫폼입니다.

## 배경 및 목적

제조·엔지니어링 현장에서는 설계 지침, 정비 매뉴얼, 규격서, 해외 논문, 납품 문서 등 방대한 기술문서가 업무의 근간을 이룹니다. 이러한 문서에 담긴 **지식의 탐색·활용·재활용**을 체계적으로 지원하기 위해 본 플랫폼을 개발하였습니다.

보안 요구로 인해 외부 네트워크가 차단된 폐쇄망 환경에서도 동작해야 하므로, 외부 CDN·클라우드 API·빌드 도구에 의존하지 않는 **완전 자립형 아키텍처**를 채택했습니다. 모든 AI 모델(LLM, 임베딩, 리랭커)은 로컬에서 구동되며, 프론트엔드는 프레임워크 없이 Vanilla JS로 작성되어 정적 웹서버만으로 배포할 수 있습니다.

플랫폼은 문서 활용의 핵심 업무 흐름에 따라 독립적인 서브시스템으로 구성됩니다.

| 서브시스템 | 역할 | 해결하는 문제 |
|------------|------|---------------|
| **Explorer** | 기술문서 탐색 | 엔지니어링 지침·가이드·규격서 등을 등록하고, AI 검색·채팅으로 필요한 지식을 빠르게 찾아 활용 |
| **Notebook**(Translator) | 문서 번역·분석 | 영문 기술문서·논문을 번역하고, AI 요약·Q&A·마인드맵으로 심층 분석하여 개인 지식으로 축적 |
| **Verify**(Compare) | 문서 비교·검증 | DOCX/PDF 문서의 버전 간 diff, AI 의미 분류, 유사도 검사(표절 탐지), 문서 규칙 검증·스코어링 수행 |

필요에 따라 서브시스템을 추가하여 플랫폼을 확장할 수 있습니다 (예: Author — 다문서 비교 분석 기반 규격서 초안 생성).

## 주요 특징

### Explorer (기술문서 탐색)
- **계층적 트리 메뉴**: JSON 기반 동적 메뉴, 3단계 깊이
- **통합 검색**: 사전 인덱싱 방식, 키워드 + FAISS 벡터 검색 RRF 병합
- **Cross-encoder 리랭커**: bge-reranker-v2-m3로 검색 정밀도 향상
- **AI 채팅**: Ollama 기반 문서 Q&A, 멀티턴 대화, 스트리밍 응답
  - **질문 라우팅**: SIMPLE/COMPARE/REASON/CHAT 4유형 자동 분류 → 최적 RAG 전략 적용
  - **쿼리 분해**: 복합 질문을 1~3개 독립 서브쿼리로 분할 → 병렬 검색 후 병합
  - **Agentic RAG**: 반복적 검색-판단-재검색 루프 (최대 3회) — 복합 추론 질문 대응
  - **LLM 프로바이더 추상화**: Ollama + OpenAI 호환 API (vLLM, NIM 등) 교체 가능
  - **채팅 UI**: 답변 복사 버튼, 스크롤-투-바텀 버튼, 어시스턴트 버블 제거 (ChatGPT/Claude 스타일)
- **구조 보존 인덱싱**: 테이블→마크다운, 수식→LaTeX 변환 후 인덱싱
- **문서 편집**: Monaco 에디터 기반 HTML 소스 편집 + 실시간 미리보기
- **문서 업로드/변환**: Word(.docx)/PDF 업로드 → HTML 자동 변환
- **수식 변환**: Word OMML → MathML 네이티브 렌더링 (외부 JS 불필요)
- **장절번호 자동 평문화**: Word 다단계 목록 자동번호를 텍스트로 변환 (COM 전처리)
- **그림/표 참조 팝업**: 캡션 자동 ID, 본문 참조 클릭 시 팝업
- **항공 용어집**: 26,000+ 용어 검색, 본문 약어 자동 인식 + 클릭 팝업

### Notebook / Translator (문서 번역·분석)
- **듀얼 번역 엔진**: PDF 모드 (PDFMathTranslate, 레이아웃 보존) + 웹 뷰 모드 (Markdown 추출+번역, 편집 가능)
- **페이지별 온디맨드 번역**: 단일 또는 범위(최대 5페이지) 번역, 3초 폴링
- **듀얼 패널 뷰어**: 좌측 원문 + 우측 번역 PDF/웹뷰, 스크롤 동기화
- **문서 분석 파이프라인**: PDF 추출 → AI 요약(크기 적응형) → 마인드맵(LLM 의미 분석) 자동 생성
- **Q&A 챗봇**: 문서 기반 질의응답, 컨텍스트 폴백 체인, NDJSON 스트리밍
- **인터랙티브 마인드맵**: Markmap 트리 시각화, 노드 클릭 시 LLM 설명, 펼치기/접기/줌
- **Markdown 편집기**: Monaco 기반 분할뷰, 번역 결과 실시간 편집
- **텍스트 선택 AI 메뉴**: 원문 드래그 → 번역/요약/마킹 3버튼 액션 바
- **마킹/메모**: 형광펜 4색, popover 편집, 페이지별 목록 탐색, 플로팅 위젯
- **개인 용어집**: source/target 쌍, pdf2zh 번역 시 자동 적용
- **문서 내 검색**: 원문+번역문+메모 키워드 검색 (Ctrl+K)
- **ZIP 다운로드**: MD + 이미지 일괄 다운로드 (DRM 환경 대응)
- **개인 폴더 트리**: 폴더 생성/이동/삭제, 드래그 앤 드롭
- **카드 기반 문서 관리**: 상태별 UI (pending/translating/done/error)
- **개인 작업공간**: 사용자별 디렉토리 격리

### Verify / Compare (문서 비교·검증)
- **3-모드 허브**: 비교(diff) / 유사도 검사 / 규칙 검증 모드 전환
- **듀얼 패널 diff**: 좌우 분할 + 동기 스크롤, 추가/삭제/수정 하이라이트
- **AI 의미 분류**: Ollama 기반 변경점 자동 태깅 (주의·참고·편집 3그룹, 6태그)
- **유사도 검사**: Winnowing(L1) + bge-m3 시맨틱 임베딩(L3) 2계층 파이프라인, 6종 유사도 지표
- **규칙 엔진**: 21종 검증 규칙 (번호 연속성, 표/그림 캡션, 금지어, 용어 통일, 문장 길이 등)
- **스코어링**: Acrolinx 밀도 방식 문서 품질 점수, 인텔리전스 패널 (스코어카드·구조·용어)
- **수락/거절 판정**: 변경점별 수락/거절/미처리, 벌크 처리
- **검토 리포트 내보내기**: XLSX, HTML, TXT 다형식 내보내기
- **스크롤바 미니맵**: 변경점 위치를 스크롤바에 마커로 표시 (PyCharm 스타일)
- **텍스트 붙여넣기**: DRM 환경 대응, 파일 없이 텍스트 직접 입력/비교
- **세션 이력**: 비교/검증 결과 자동 저장, 이력 조회

### Launcher (통합 런처)
- 각 시스템(Explorer, Notebook, Verify, Settings)으로의 진입점
- 시스템 스위처: SVG 아이콘, 호버 드롭다운, 미구현 시스템(Author 등) 뱃지 표시

### 공통 기능
- **3단계 RBAC 인증**: viewer / editor / admin 역할 기반 접근 제어
- **다크/라이트 모드**: 테마 전환, localStorage 저장
- **관리자 설정 페이지**: 웹 GUI로 AI/RAG, 세션, 보안, 업로드, 화면 설정
- **사용자 접속 통계**: 실시간 접속자 수, 페이지뷰, 활동 대시보드
- **에어갭 환경 최적화**: 모든 리소스 로컬 포함, CDN/프레임워크/빌드 도구 불필요
- **렌더링 최적화**: 대용량 문서 `content-visibility:auto` 섹션 래핑
- **운영 안정성**: 원자적 JSON 쓰기(tmp→rename), 그레이스풀 셧다운, 스턱 태스크 자동 복구, 로테이팅 로그

## 빠른 시작

### 방법 A: Docker (권장)

```bash
docker compose up -d
# → http://localhost 으로 접속
```

> 상세 설정 및 폐쇄망 배포는 [DOCKER-OPERATIONS](docs/03-DOCKER-OPERATIONS.md) 참조.
> 배포 환경 3종(개발 PC · 회사 Linux VM · 회사 Windows PC) 전체 흐름은 [DEPLOYMENT-GUIDE](docs/01-DEPLOYMENT-GUIDE.md) 참조.

### 방법 B: 로컬 Python

#### 1. 프론트엔드 실행

```bash
cd smart-document-platform
python -m http.server 8080
```

#### 2. 백엔드 실행 (AI/편집/인증 기능)

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

### 접속

- Launcher: `http://localhost:8080/launcher.html` (로컬) / `http://localhost/launcher.html` (Docker)
- Explorer: `http://localhost:8080/` (로컬) / `http://localhost/` (Docker)
- Notebook(Translator): `http://localhost:8080/translator.html`
- Verify(Compare): `http://localhost:8080/compare.html`

> 콘텐츠 열람/검색/AI 채팅은 로그인 없이 가능합니다.
> 문서 업로드/편집/인덱싱은 admin 로그인이 필요합니다.

### 4. 관리자 계정 생성

```bash
python tools/create-admin.py
```

### 5. 상세 가이드

**설치·배포** (이 순서로 읽으세요)

| 순서 | 문서 | 설명 |
|------|------|------|
| 1 | [DEPLOYMENT-GUIDE](docs/01-DEPLOYMENT-GUIDE.md) | 배포 환경 3종(개발 PC · 회사 Linux · 회사 Windows) 통합 가이드 — 신규 배포자의 필수 입구 |
| 2 | [BACKEND-SETUP](docs/02-BACKEND-SETUP.md) | Python 백엔드 심화 — 가상환경, 오프라인 패키지, 변환기 의존성 |
| 3 | [DOCKER-OPERATIONS](docs/03-DOCKER-OPERATIONS.md) | Docker 배포·패치·백업·롤백 심화 |
| 4 | [USER-GUIDE](docs/04-USER-GUIDE.md) | 사용자·관리자 기능, 메뉴·콘텐츠 관리 |

**기술 참조**

| 문서 | 설명 |
|------|------|
| [ARCHITECTURE](docs/05-ARCHITECTURE.md) | 시스템 구성도 (Docker + Windows 네이티브), 폴더 구조, API 전체 목록 |
| [RAG-PIPELINE](docs/06-RAG-PIPELINE.md) | RAG 파이프라인 구현 사양 — 모듈·파라미터·엔드포인트 |
| [RAG-TECHNICAL-REPORT](docs/RAG-TECHNICAL-REPORT.md) | RAG 품질 개선 근거·실험 수치·의사결정 히스토리 |
| [TRANSLATOR-SYSTEM](docs/07-TRANSLATOR-SYSTEM.md) | Notebook(Translator) 시스템 설계 — 번역·추출·요약·Q&A·마인드맵 |
| [VERIFY-SYSTEM](docs/11-VERIFY-SYSTEM.md) | Verify 시스템 — 비교·유사도·규칙 엔진·스코어링·검토 리포트 통합 |
| [CONVERTER-ARCHITECTURE](docs/13-CONVERTER-ARCHITECTURE.md) | DOCX→HTML 변환기 — 엔진 SSOT + 전처리 어댑터 체인 (Plan-37) |

**운영·전략**

| 문서 | 설명 |
|------|------|
| [PLATFORM-VISION](docs/09-PLATFORM-VISION.md) | 플랫폼 발전 방향, 로드맵, 외부 연계(K-Spec) |

**아카이브·참고** (`workbench/`)
- `workbench/reports/plan-11-production-readiness.md` — 운영 준비도 평가 보고서 (Plan-11, Plan-22/27 완료 반영)
- `workbench/reference/git-initial-setup.md` — 프로젝트 초기 Git 설정 가이드

## 프로젝트 구조

```
smart-document-platform/
├── index.html              # Explorer 메인 페이지 (3-패널 레이아웃)
├── translator.html         # Notebook(Translator) PDF 번역·분석 뷰어
├── compare.html            # Verify(Compare) 문서 비교·검증
├── launcher.html           # Launcher 통합 진입점
├── login.html              # 독립 로그인 페이지
├── admin.html              # 관리자 설정 페이지
├── css/                    # 스타일시트
│   ├── tokens.css         # 디자인 토큰 (CSS 변수, 리셋, 포커스 링)
│   ├── components.css     # 공통 컴포넌트 (버튼, 입력, 배지, 스피너, 슬라이더, 툴팁)
│   ├── modal.css          # 공통 모달 스타일
│   ├── scrollbar.css      # 공통 스크롤바 스타일
│   ├── toast.css          # 공통 토스트 알림 스타일
│   ├── platform-header.css # 공통 헤더 스타일
│   ├── platform-footer.css # 공통 푸터 스타일
│   ├── main.css           # 전체 레이아웃 및 테마
│   ├── tree-menu.css      # 좌측 트리 메뉴
│   ├── content.css        # 콘텐츠, 섹션 네비게이터, 렌더링 최적화
│   ├── ai-chat.css        # AI 채팅 UI
│   ├── editor.css         # 문서 편집기 UI
│   ├── figure-popup.css   # 그림/표 팝업
│   ├── bookmarks.css      # 북마크 오버레이
│   ├── glossary.css       # 용어집 + 약어 팝업
│   ├── auth.css           # 인증 UI
│   ├── analytics.css      # 접속 통계 대시보드
│   ├── admin-settings.css # 관리자 설정 페이지
│   ├── translator.css     # Notebook 뷰어 스타일
│   ├── compare.css        # Verify 전용 스타일
│   └── images/            # UI 이미지 (로고, 배너 등)
├── js/                     # JavaScript
│   ├── app.js             # 메인 앱 로직, 렌더링 최적화, 스크롤 내비게이션
│   ├── config.js          # AI/편집기/인증 설정
│   ├── auth.js            # 인증 모듈 (3단계 RBAC)
│   ├── ai-chat.js         # AI 채팅 기능
│   ├── editor.js          # Monaco 에디터 기반 문서 편집기 (Explorer)
│   ├── editor-core.js     # 공통 편집기 코어 (Monaco 래퍼, Strategy 패턴)
│   ├── tree-menu.js       # 트리 메뉴 렌더링
│   ├── section-nav.js     # 우측 섹션 네비게이터
│   ├── search.js          # 검색 기능
│   ├── banner.js          # 배너 슬라이드쇼
│   ├── figure-popup.js    # 그림/표 참조 팝업
│   ├── bookmarks.js       # 헤딩 북마크
│   ├── glossary.js        # 용어집 + 약어 하이라이트
│   ├── keyboard.js        # 키보드 단축키
│   ├── analytics.js       # 접속 통계
│   ├── admin-settings.js  # 관리자 설정 페이지
│   ├── translator.js      # Notebook 뷰어 로직 (PDF.js, 마킹, AI 분석, 용어집, Q&A)
│   ├── toast.js           # 공통 토스트 알림 (Notebook/Verify 공용)
│   ├── platform-header.js # 공통 헤더 (테마 토글, 시스템 스위처)
│   ├── platform-footer.js # 공통 푸터
│   ├── lib/pdfjs/         # PDF.js v3.11.174 (Notebook용)
│   └── lib/markmap/       # Markmap 마인드맵 (d3.min.js, markmap-view.js)
├── data/                   # 데이터 파일
│   ├── menu.json          # 메뉴 구조 정의
│   ├── search-index.json  # 검색 인덱스
│   ├── vector-index.faiss # FAISS 벡터 인덱스
│   ├── vector-index_meta.json # 벡터 인덱스 메타데이터
│   ├── settings.json      # 런타임 설정 오버라이드
│   ├── auth.db            # 사용자/세션 DB (SQLite)
│   ├── analytics.db       # 접속 통계 DB (SQLite)
│   ├── glossary.json      # 항공 용어집 (26,000+)
│   ├── compare-rules.json # Verify 검증 규칙 정의
│   ├── boilerplate-phrases.json # 유사도 검사 보일러플레이트 제외 구문
│   ├── translator/        # Notebook 개인 작업공간 ({username}/{doc_id}/)
│   ├── compare/           # Verify 세션 데이터
│   └── verify/            # Verify 검증 결과
├── contents/               # HTML 콘텐츠
├── backend/                # FastAPI 백엔드
│   ├── main.py            # 진입점 (lifespan, 헬스체크, CORS, 스턱 태스크 복구)
│   ├── config.py          # 백엔드 설정 (LLM, 검색, 인증, 번역, 비교 등)
│   ├── dependencies.py    # FastAPI 의존성 (인증 미들웨어)
│   ├── requirements.txt   # 의존성 패키지
│   ├── api/               # API 엔드포인트
│   │   ├── auth.py        # 인증 API (로그인/로그아웃/사용자 CRUD)
│   │   ├── search.py      # 검색 API (키워드/벡터/하이브리드)
│   │   ├── chat.py        # 채팅 API (RAG, 스트리밍, 피드백)
│   │   ├── document.py    # 문서 저장/이력/복원 API
│   │   ├── upload.py      # 업로드/변환/인덱싱 API
│   │   ├── menu.py        # 메뉴 트리 API
│   │   ├── translator.py  # Notebook API (번역, 추출, 요약, Q&A, 마킹, 폴더, 용어집)
│   │   ├── compare.py     # Verify API (diff, AI 분류, 유사도, 규칙 검증, 내보내기)
│   │   ├── settings.py    # 설정 API
│   │   └── analytics.py   # 통계 API
│   └── services/          # 비즈니스 로직
│       ├── translator_service.py  # 번역/추출/요약 오케스트레이션, 폴더·메타 관리
│       ├── ai_summary.py         # 크기 적응형 AI 요약 + 마인드맵 트리 생성
│       ├── notebook_chat.py      # 문서 Q&A (컨텍스트 폴백, 스트리밍)
│       ├── md_extractor.py       # PDF → Markdown 추출 (PyMuPDF + DocLayout-YOLO)
│       ├── md_translator.py      # Markdown 블록 번역 + 병합
│       ├── text_translator.py    # 단일/배치 텍스트 번역
│       ├── compare_service.py    # 텍스트 추출, AI 의미 분류
│       ├── similarity_engine.py  # 유사도 검사 (Winnowing + 시맨틱 임베딩)
│       ├── rule_engine.py        # 문서 규칙 검증 엔진 (21종)
│       ├── export_service.py     # 검토 리포트 내보내기 (XLSX/HTML/TXT)
│       ├── doc_converter.py      # 문서 변환 (DOCX/PDF → HTML)
│       ├── document_extractor.py # 문서 텍스트 추출 (HTML/PDF/DOCX)
│       ├── keyword_search.py     # 키워드 검색 (BM25)
│       ├── vector_search.py      # FAISS 벡터 검색 + RRF 병합
│       ├── embedding_client.py   # 임베딩 클라이언트 (로컬/Ollama)
│       ├── reranker.py           # Cross-encoder 리랭킹
│       ├── conversation.py       # 대화 세션 저장소
│       ├── query_rewriter.py     # LLM 쿼리 재작성
│       ├── question_router.py    # 질문 유형 분류 (SIMPLE/COMPARE/REASON/CHAT)
│       ├── query_decomposer.py   # 복합 쿼리 분해 (1~3개 서브쿼리)
│       ├── rag_agent.py          # Agentic RAG 반복 검색-판단 루프
│       ├── llm_provider.py       # LLM 프로바이더 추상화 (Ollama/OpenAI 호환)
│       ├── llm_client.py         # LLM 응답 생성 래퍼 (동기/스트리밍)
│       ├── korean_tokenizer.py   # 한국어 형태소 분석 (kiwipiepy, 폴백: 공백 분리)
│       ├── auth.py               # 인증 서비스 (세션, 패스워드 해싱)
│       ├── analytics.py          # 통계 서비스 (SQLite, 대시보드 집계)
│       └── settings_service.py   # settings.json CRUD, 런타임 반영
│   └── rules/              # 규칙 엔진 정의 (Verify)
│       ├── custom.json     # 자체 규칙 6종
│       ├── mil-structure.json # MIL-STD 구조 규칙 7종
│       └── ste-writing.json   # ASD-STE100 작성 규칙 8종
├── models/                 # 로컬 리랭커 모델 (bge-reranker-v2-m3)
├── tools/                  # 유틸리티 스크립트
│   ├── build-search-index.py  # 검색 인덱스 생성
│   ├── build-vector-index.py  # FAISS 벡터 인덱스 빌드
│   ├── html_to_text.py        # HTML→검색텍스트 변환 (테이블→GFM, 수식→LaTeX)
│   ├── create-admin.py        # CLI admin 계정 생성
│   ├── daily-backup.py        # 일일 백업 스크립트
│   ├── excel-to-menu.py       # Excel→메뉴 구조 변환
│   ├── import-glossary.py     # 용어집 임포트
│   └── converter/             # 문서 변환기 (DOCX/PDF → HTML)
├── Dockerfile              # FastAPI 백엔드 컨테이너
├── docker-compose.yml      # 프로덕션 오케스트레이션
├── docker/                 # Docker 설정 (Nginx Dockerfile, conf)
├── deploy.sh               # 전체 이미지 배포 스크립트
├── patch-apply.sh          # 패치 적용 스크립트
└── docs/                   # 문서
    ├── 01-DEPLOYMENT-GUIDE.md     # 배포 환경 3종 통합 가이드 (입구)
    ├── 02-BACKEND-SETUP.md        # Python 백엔드 심화 설정
    ├── 03-DOCKER-OPERATIONS.md    # Docker 배포·운영 심화
    ├── 04-USER-GUIDE.md           # 사용자/관리자 가이드
    ├── 05-ARCHITECTURE.md         # 시스템 아키텍처, 폴더 구조, API
    ├── 06-RAG-PIPELINE.md         # RAG 구현 사양
    ├── 07-TRANSLATOR-SYSTEM.md    # Notebook(Translator) 설계
    ├── 09-PLATFORM-VISION.md      # 플랫폼 비전, 로드맵
    ├── 11-VERIFY-SYSTEM.md        # Verify 시스템 통합 (비교·유사도·규칙·리포트)
    ├── 13-CONVERTER-ARCHITECTURE.md # DOCX→HTML 변환기 (엔진 SSOT)
    └── RAG-TECHNICAL-REPORT.md    # RAG 품질 개선 기술 보고서
```

## 기술 스택

| 구분 | 기술 |
|------|------|
| **프론트엔드** | Vanilla HTML5/CSS3/JavaScript (프레임워크 없음) |
| **백엔드** | FastAPI (Python 3.11+) |
| **AI/LLM** | Ollama (로컬 LLM, 에어갭 호환) + OpenAI 호환 API (vLLM, NIM 등) |
| **검색** | BM25 + FAISS (faiss-cpu), bge-m3 임베딩 |
| **리랭킹** | sentence-transformers, bge-reranker-v2-m3 |
| **PDF** | PDF.js v3.11.174 (뷰어), PDFMathTranslate/pdf2zh (번역), PyMuPDF (추출) |
| **문서 분석** | PyMuPDF4LLM + DocLayout-YOLO (레이아웃 추출), Ollama (AI 요약/Q&A) |
| **마인드맵** | Markmap (d3.js 기반, 로컬 IIFE 번들) |
| **데이터** | JSON, SQLite (auth.db) |
| **웹서버** | Apache Tomcat / Python http.server |

## 시스템 요구사항

- **브라우저**: Chrome, Edge, Firefox (최신 버전 권장)
- **Python**: 3.11 이상 (백엔드, 검색 인덱스 생성용)
- **웹 서버**: Apache Tomcat 7.0+ 또는 Python http.server (개발용)
- **Ollama**: AI 채팅 + 임베딩 + 번역 기능 사용 시 필요 (선택사항)

## 확장 가능한 서브시스템 아이디어

본 플랫폼은 Launcher를 통해 서브시스템을 자유롭게 추가할 수 있는 구조입니다. 제조·엔지니어링 업무와 IT 트렌드를 고려할 때, 다음과 같은 시스템이 향후 확장 후보가 될 수 있습니다.

### 문서 관련

| 시스템 | 설명 |
|--------|------|
| **Verify** (문서 비교·검증) ✅ | 구현 완료 — diff, AI 의미 분류, 유사도 검사, 21종 규칙 엔진, 스코어링, XLSX 내보내기 |
| **Author** (문서 작성 보조) 📐 | 설계 단계 — 다문서 비교 분석 → 비교 매트릭스 → 규격서 초안 자동 생성 (Plan-24) |
| **Archive** (문서 아카이브) | 문서 이력·버전 관리, 만료/갱신 주기 알림, 규격 개정 이력 타임라인. 품질 감사 대비 문서 추적성 확보 |

### 지식 활용

| 시스템 | 설명 |
|--------|------|
| **Lesson** (교훈 관리) | 프로젝트·정비 과정의 교훈(Lessons Learned) 등록·검색·재활용. 유사 사례 AI 추천으로 반복 실수 방지 |
| **Training** (교육 지원) | 기술문서 기반 퀴즈·체크리스트 자동 생성, 신입 엔지니어 온보딩 학습 경로 구성 |
| **Wiki** (사내 위키) | 부서별 암묵지·노하우를 구조화된 위키로 축적, AI 검색과 연동하여 조직 지식 자산화 |

### 업무 효율

| 시스템 | 설명 |
|--------|------|
| **Dashboard** (현황 대시보드) | 문서 등록·번역·검색 활용 통계, 부서별 지식 활용도 시각화. 관리자용 운영 인사이트 제공 |
| **Connector** (외부 연동) | 사내 PLM/PDM·ERP·이슈 트래커와 연동하여 문서 메타데이터 자동 동기화, 업무 맥락 기반 문서 추천 |
| **Reviewer** (검토 워크플로) | 문서 검토·승인 프로세스 관리, 코멘트·마크업, 검토 이력 추적. 다부서 협업 문서의 품질 게이트 역할 |

> **참고**: 위 아이디어는 제조업 디지털 전환(DX), 지식관리(KM), AI 문서 처리 트렌드를 바탕으로 정리한 것입니다. 플랫폼의 모듈형 구조(Launcher + 독립 서브시스템)를 활용하면 각 시스템을 우선순위에 따라 점진적으로 추가할 수 있습니다.

## 라이선스

이 프로젝트는 내부 기술문서 관리를 위해 제작되었습니다.

## 지원

문제가 발생하거나 개선 사항이 있으면 프로젝트 관리자에게 문의하세요.

---

**Smart Document Platform** - 에어갭 환경을 위한 AI 기술문서 포털 플랫폼
