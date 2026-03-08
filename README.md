# Smart Document Platform

에어갭(폐쇄망) 환경에서 사용 가능한 AI 기반 기술문서 웹 플랫폼입니다.
3개의 독립 시스템(**Explorer**, **Translator**, **Launcher**)으로 구성됩니다.

## 주요 특징

### Explorer (기술문서 포털)
- **계층적 트리 메뉴**: JSON 기반 동적 메뉴, 3단계 깊이
- **통합 검색**: 사전 인덱싱 방식, 키워드 + FAISS 벡터 검색 RRF 병합
- **Cross-encoder 리랭커**: bge-reranker-v2-m3로 검색 정밀도 향상
- **AI 채팅**: Ollama 기반 문서 Q&A, 멀티턴 대화, 스트리밍 응답
- **구조 보존 인덱싱**: 테이블→마크다운, 수식→LaTeX 변환 후 인덱싱
- **문서 편집**: Monaco 에디터 기반 HTML 소스 편집 + 실시간 미리보기
- **문서 업로드/변환**: Word(.docx)/PDF 업로드 → HTML 자동 변환
- **수식 변환**: Word OMML → MathML 네이티브 렌더링 (외부 JS 불필요)
- **장절번호 자동 평문화**: Word 다단계 목록 자동번호를 텍스트로 변환 (COM 전처리)
- **그림/표 참조 팝업**: 캡션 자동 ID, 본문 참조 클릭 시 팝업
- **항공 용어집**: 26,000+ 용어 검색, 본문 약어 자동 인식 + 클릭 팝업

### Translator (PDF 번역 뷰어)
- **듀얼 번역 엔진**: PDF 모드 (PDFMathTranslate, 레이아웃 보존) + 텍스트 모드 (자체 렌더링, 폰트 조절)
- **페이지별 온디맨드 번역**: 단일 또는 범위(최대 5페이지) 번역, 3초 폴링
- **듀얼 패널 뷰어**: 좌측 원문 + 우측 번역 PDF, 스크롤 동기화
- **텍스트 선택 AI 메뉴**: 원문 드래그 → 번역/요약/마킹 3버튼 액션 바
- **마킹/메모**: 형광펜 4색, popover 편집, 페이지별 목록 탐색, 플로팅 위젯
- **개인 폴더 트리**: 폴더 생성/이동/삭제, 드래그 앤 드롭
- **카드 기반 문서 관리**: 상태별 UI (pending/translating/done/error)
- **개인 작업공간**: 사용자별 디렉토리 격리

### Launcher (통합 런처)
- 각 시스템(Explorer, Translator, Settings)으로의 진입점
- 시스템 스위처: SVG 아이콘, 호버 드롭다운, 미구현 시스템 뱃지 표시

### 공통 기능
- **3단계 RBAC 인증**: viewer / editor / admin 역할 기반 접근 제어
- **다크/라이트 모드**: 테마 전환, localStorage 저장
- **관리자 설정 페이지**: 웹 GUI로 AI/RAG, 세션, 보안, 업로드, 화면 설정
- **사용자 접속 통계**: 실시간 접속자 수, 페이지뷰, 활동 대시보드
- **에어갭 환경 최적화**: 모든 리소스 로컬 포함, CDN/프레임워크/빌드 도구 불필요
- **렌더링 최적화**: 대용량 문서 `content-visibility:auto` 섹션 래핑

## 빠른 시작

### 1. 프론트엔드 실행

```bash
cd smart-document-platform
python -m http.server 8080
```

### 2. 백엔드 실행 (AI/편집/인증 기능)

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

### 3. 접속

- Explorer: `http://localhost:8080/`
- Translator: `http://localhost:8080/translator.html`
- Launcher: `http://localhost:8080/launcher.html`

> 콘텐츠 열람/검색/AI 채팅은 로그인 없이 가능합니다.
> 문서 업로드/편집/인덱싱은 admin 로그인이 필요합니다.

### 4. 관리자 계정 생성

```bash
python tools/create-admin.py
```

### 5. 상세 가이드

처음 사용하는 경우 아래 순서로 읽으세요.

| 순서 | 문서 | 설명 |
|------|------|------|
| 1 | [QUICK-START](docs/01-QUICK-START.md) | 로컬 PC에서 바로 테스트 (Python) |
| 2 | [INSTALLATION](docs/02-INSTALLATION.md) | Tomcat 서버 설치 (프론트엔드) |
| 3 | [BACKEND-SETUP](docs/03-BACKEND-SETUP.md) | FastAPI 백엔드 설치 (AI 채팅) |
| 4 | [USER-GUIDE](docs/04-USER-GUIDE.md) | 메뉴/콘텐츠 관리, 운영 방법 |

**기술 참조**

| 문서 | 설명 |
|------|------|
| [ARCHITECTURE](docs/05-ARCHITECTURE.md) | 시스템 구성도, 서버별 설치 항목, API 설계 |
| [RAG-PIPELINE](docs/06-RAG-PIPELINE.md) | 검색/AI 파이프라인, 임베딩, 청킹 전략 |
| [TRANSLATOR-SYSTEM](docs/07-TRANSLATOR-SYSTEM.md) | Translator PDF 번역 뷰어 기술 문서 |

**개발/전략**

| 문서 | 설명 |
|------|------|
| [GIT-GUIDE](docs/08-GIT-GUIDE.md) | Git 사용법, GitHub 연동, 브랜치 전략 |
| [PLATFORM-VISION](docs/09-PLATFORM-VISION.md) | 플랫폼 발전 방향, 로드맵 |

**부록**

| 문서 | 설명 |
|------|------|
| [RAG-TECHNICAL-REPORT](docs/RAG-TECHNICAL-REPORT.md) | RAG 답변 품질 개선 기술 보고서 |

## 프로젝트 구조

```
smart-document-platform/
├── index.html              # Explorer 메인 페이지 (3-패널 레이아웃)
├── translator.html             # Translator PDF 번역 뷰어
├── launcher.html           # Launcher 통합 진입점
├── login.html              # 독립 로그인 페이지
├── css/                    # 스타일시트
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
│   └── images/            # UI 이미지 (로고, 배너 등)
├── js/                     # JavaScript
│   ├── app.js             # 메인 앱 로직, 렌더링 최적화, 스크롤 내비게이션
│   ├── config.js          # AI/편집기/인증 설정
│   ├── auth.js            # 인증 모듈 (3단계 RBAC)
│   ├── ai-chat.js         # AI 채팅 기능
│   ├── editor.js          # Monaco 에디터 기반 문서 편집기
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
│   └── lib/pdfjs/         # PDF.js v3.11.174 (Translator용)
├── data/                   # 데이터 파일
│   ├── menu.json          # 메뉴 구조 정의
│   ├── search-index.json  # 검색 인덱스
│   ├── vector-index/      # FAISS 벡터 인덱스
│   ├── settings.json      # 런타임 설정 오버라이드
│   ├── auth.db            # 사용자/세션 DB
│   ├── glossary.json      # 항공 용어집 (26,000+)
│   └── translator/        # Translator 데이터 ({username}/{doc_id}/)
├── contents/               # HTML 콘텐츠
├── backend/                # FastAPI 백엔드
│   ├── main.py            # 진입점
│   ├── config.py          # 백엔드 설정
│   ├── dependencies.py    # FastAPI 의존성
│   ├── requirements.txt   # 의존성 패키지
│   ├── api/               # API 엔드포인트
│   │   ├── translator.py     # Translator API (업로드, 번역, PDF 서빙, AI 선택, 마킹)
│   │   ├── settings.py   # 설정 API
│   │   ├── analytics.py  # 통계 API
│   │   └── auth.py       # 인증 API
│   └── services/          # 비즈니스 로직
│       ├── translator_service.py  # PMT 번역, 개인 작업공간, 메타 관리, AI 선택
│       ├── text_translator.py    # 텍스트 모드 번역 엔진 (PyMuPDF + YOLO + Ollama)
│       ├── keyword_search.py  # 키워드 검색
│       ├── vector_search.py   # FAISS 벡터 검색 + RRF 병합
│       ├── reranker.py        # Cross-encoder 리랭킹
│       ├── conversation.py    # 대화 세션 저장소
│       ├── query_rewriter.py  # LLM 쿼리 재작성
│       └── settings_service.py # settings.json CRUD
├── models/                 # 로컬 리랭커 모델 (bge-reranker-v2-m3)
├── tools/                  # 유틸리티 스크립트
│   ├── build-search-index.py  # 검색 인덱스 생성
│   ├── build-vector-index.py  # FAISS 벡터 인덱스 빌드
│   ├── html_to_text.py        # HTML→검색텍스트 변환
│   ├── create-admin.py        # CLI admin 계정 생성
│   └── converter/             # 문서 변환기 (DOCX/PDF → HTML)
└── docs/                   # 문서
    ├── 01-QUICK-START.md
    ├── 02-INSTALLATION.md
    ├── 03-BACKEND-SETUP.md
    ├── 04-USER-GUIDE.md
    ├── 05-ARCHITECTURE.md
    ├── 06-RAG-PIPELINE.md
    ├── 07-TRANSLATOR-SYSTEM.md
    ├── 08-GIT-GUIDE.md
    ├── 09-PLATFORM-VISION.md
    └── RAG-TECHNICAL-REPORT.md
```

## 기술 스택

| 구분 | 기술 |
|------|------|
| **프론트엔드** | Vanilla HTML5/CSS3/JavaScript (프레임워크 없음) |
| **백엔드** | FastAPI (Python 3.11+) |
| **AI/LLM** | Ollama (로컬 LLM, 에어갭 호환) |
| **검색** | BM25 + FAISS (faiss-cpu), bge-m3 임베딩 |
| **리랭킹** | sentence-transformers, bge-reranker-v2-m3 |
| **PDF** | PDF.js v3.11.174 (뷰어), PDFMathTranslate/pdf2zh (번역), PyMuPDF (페이지 수 추출) |
| **데이터** | JSON, SQLite (auth.db) |
| **웹서버** | Apache Tomcat / Python http.server |

## 시스템 요구사항

- **브라우저**: Chrome, Edge, Firefox (최신 버전 권장)
- **Python**: 3.11 이상 (백엔드, 검색 인덱스 생성용)
- **웹 서버**: Apache Tomcat 7.0+ 또는 Python http.server (개발용)
- **Ollama**: AI 채팅 + 임베딩 + 번역 기능 사용 시 필요 (선택사항)

## 라이선스

이 프로젝트는 내부 기술문서 관리를 위해 제작되었습니다.

## 지원

문제가 발생하거나 개선 사항이 있으면 프로젝트 관리자에게 문의하세요.

---

**Smart Document Platform** - 에어갭 환경을 위한 AI 기술문서 포털 플랫폼
