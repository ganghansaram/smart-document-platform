# KF-21 History WebBook Template (v5.5)

에어갭(폐쇄망) 환경에서 사용 가능한 AI 기반 기술문서 웹 플랫폼입니다.

## 주요 특징

- ✅ **설치 간편**: Apache Tomcat에 폴더 복사만으로 즉시 서비스 가능
- ✅ **외부 의존성 없음**: CDN, 프레임워크, 빌드 도구 불필요
- ✅ **에어갭 환경 최적화**: 모든 리소스를 로컬에 포함
- ✅ **쉬운 관리**: JSON 파일 수정만으로 메뉴 구조 변경
- ✅ **강력한 검색**: 사전 인덱싱 방식의 빠른 전체 문서 검색
- ✅ **하이브리드 검색**: BM25 키워드 + FAISS 벡터 검색 (RRF 점수 병합)
- ✅ **Cross-encoder 리랭커**: bge-reranker-v2-m3로 검색 정밀도 향상
- ✅ **멀티턴 대화**: 후속 질문 컨텍스트 유지, LLM 쿼리 재작성
- ✅ **구조 보존 인덱싱**: 테이블→마크다운, 수식→LaTeX 변환 후 인덱싱
- ✅ **AI 채팅**: Ollama 기반 문서 Q&A (로컬 LLM, 에어갭 호환)
- ✅ **문서 편집**: Monaco 에디터 기반 HTML 소스 편집 + 실시간 미리보기
- ✅ **문서 업로드/변환**: Word(.docx)/PDF 파일 업로드 → HTML 자동 변환
- ✅ **장절번호 자동 평문화**: Word 다단계 목록 자동번호를 텍스트로 변환 (COM 전처리)
- ✅ **그림/표 참조 팝업**: 캡션 자동 ID 부여, 본문 참조 클릭 시 팝업 표시
- ✅ **수식 변환**: Word OMML → MathML 네이티브 렌더링 (외부 JS 불필요)
- ✅ **다크/라이트 모드**: 해/달 아이콘으로 테마 전환, localStorage 저장
- ✅ **북마크**: 헤딩 북마크 저장 + 문서 간 이동, localStorage 저장
- ✅ **항공 용어집**: 26,000+ 용어 검색/탐색, 본문 약어 자동 인식 + 클릭 팝업
- ✅ **렌더링 최적화**: 대용량 문서 `content-visibility:auto` 섹션 래핑
- ✅ **배너 슬라이드쇼**: 이미지 + 영상 혼합 슬라이드, Ken Burns 효과
- ✅ **키보드 단축키**: ?/←→/H/B 단축키, 도움말 모달
- ✅ **브레드크럼 내비게이션**: 현재 문서 경로 표시, 상위 메뉴 클릭 이동
- ✅ **3단계 RBAC 인증**: viewer(열람) / editor(편집) / admin(관리) 역할 기반 접근 제어, 독립 로그인 페이지
- ✅ **통합 토스트 알림**: 작업 결과 피드백 (저장, 업로드, 북마크 등)
- ✅ **현대적 UI**: 록히드마틴 스타일의 깔끔한 디자인, 통계 스트립
- ✅ **3단계 RBAC**: viewer / editor / admin 역할 기반 접근 제어
- ✅ **독립 로그인 페이지**: 다크 그래디언트 디자인, 로그인 성공 시 fade-out 전환
- ✅ **관리자 설정 페이지**: 웹 GUI로 AI/RAG, 세션, 보안, 업로드, 화면 설정 실시간 변경
- ✅ **사용자 접속 통계**: 실시간 접속자 수, 페이지뷰, 활동 대시보드
- ✅ **사이트 타이틀 커스터마이징**: 관리자 설정에서 사이트 이름 변경 (플랫폼명 WebBook 고정)

## 빠른 시작

### 1. 설치

```bash
# Tomcat webapps/ROOT 폴더에 복사
cp -r kf21-webbook-template/* /path/to/tomcat/webapps/ROOT/

# Tomcat 재시작
systemctl restart tomcat
```

### 2. 관리자 계정 생성 (백엔드 사용 시)

```bash
python tools/create-admin.py
```

### 3. 접속

브라우저에서 `http://서버IP:8080/` 접속

> 콘텐츠 열람/검색/AI 채팅은 로그인 없이 가능합니다.
> 문서 업로드/편집/인덱싱은 admin 로그인이 필요합니다.

### 4. 상세 가이드

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
| [ARCHITECTURE](docs/ARCHITECTURE.md) | 시스템 구성도, 서버별 설치 항목, API 설계 |
| [RAG-PIPELINE](docs/RAG-PIPELINE.md) | 검색/AI 파이프라인, 임베딩, 청킹 전략 |
| [RAG-TECHNICAL-REPORT](docs/RAG-TECHNICAL-REPORT.md) | RAG 답변 품질 개선 기술 보고서 |
| [GIT-GUIDE](docs/GIT-GUIDE.md) | Git 사용법, GitHub 연동, 브랜치 전략 |

## 프로젝트 구조

```
kf21-webbook-template/
├── index.html              # 메인 페이지 (3-패널 레이아웃)
├── login.html              # 독립 로그인 페이지 (다크 디자인)
├── css/                    # 스타일시트
│   ├── main.css           # 전체 레이아웃 및 테마
│   ├── tree-menu.css      # 좌측 트리 메뉴
│   ├── content.css        # 콘텐츠, 섹션 네비게이터, 렌더링 최적화
│   ├── ai-chat.css        # AI 채팅 UI
│   ├── editor.css         # 문서 편집기 UI
│   ├── figure-popup.css   # 그림/표 팝업 스타일
│   ├── bookmarks.css      # 북마크 오버레이 + 헤딩 아이콘 스타일
│   ├── glossary.css       # 용어집 페이지 + 본문 약어 팝업 스타일
│   ├── auth.css           # 인증 UI (로그인/사용자 관리 모달)
│   ├── analytics.css      # 접속 통계 대시보드
│   ├── admin-settings.css # 관리자 설정 페이지
│   └── images/            # UI 이미지 (로고, 배너 등)
├── js/                     # JavaScript
│   ├── app.js             # 메인 앱 로직, 렌더링 최적화, 스크롤 내비게이션
│   ├── tree-menu.js       # 트리 메뉴 렌더링
│   ├── section-nav.js     # 우측 섹션 네비게이터
│   ├── search.js          # 검색 기능
│   ├── banner.js          # 배너 슬라이드쇼 및 홈페이지 섹션 링크
│   ├── config.js          # AI/편집기/인증 설정 (Ollama URL, 모델명, 백엔드 URL)
│   ├── auth.js            # 인증 모듈 (로그인/로그아웃/사용자 관리)
│   ├── ai-chat.js         # AI 채팅 기능
│   ├── editor.js          # Monaco 에디터 기반 문서 편집기
│   ├── figure-popup.js    # 그림/표 참조 팝업 모달
│   ├── bookmarks.js       # 헤딩 북마크 CRUD + 오버레이 UI
│   ├── glossary.js        # 용어집 페이지 + 본문 약어 하이라이트/팝업
│   ├── keyboard.js        # 키보드 단축키 + 도움말 모달
│   ├── analytics.js       # 접속 통계 (heartbeat, 대시보드)
│   └── admin-settings.js  # 관리자 설정 페이지 (탭 GUI)
├── data/                   # 데이터 파일
│   ├── menu.json          # 메뉴 구조 정의
│   ├── search-index.json  # 검색 인덱스
│   ├── vector-index/      # FAISS 벡터 인덱스 (.faiss + _meta.json)
│   ├── settings.json      # 런타임 설정 오버라이드 (관리자 설정에서 저장)
│   ├── auth.db            # 사용자/세션 DB (서버 시작 시 자동 생성)
│   ├── glossary.json      # 항공 용어집 (26,000+ 용어)
│   └── glossary.csv       # 용어집 CSV 원본 (관리용)
├── contents/               # HTML 콘텐츠
│   ├── home.html
│   ├── about.html
│   ├── dev-overview/      # 카테고리별 폴더
│   └── images/            # 이미지 파일
├── backend/                # FastAPI 백엔드 (AI 채팅 + 문서 편집 + 인증)
│   ├── main.py            # 진입점
│   ├── config.py          # 백엔드 설정 (임베딩, 리랭커, 멀티턴, 인증)
│   ├── dependencies.py    # FastAPI 의존성 (require_admin)
│   ├── requirements.txt   # 의존성 패키지
│   ├── api/               # API 엔드포인트 (auth.py 포함)
│   │   ├── settings.py         # 설정 API (GET/POST /api/settings)
│   │   └── analytics.py        # 통계 API (heartbeat, dashboard)
│   ├── services/          # 비즈니스 로직 (auth.py 포함)
│   │   ├── keyword_search.py    # 키워드 검색
│   │   ├── vector_search.py     # FAISS 벡터 검색 + 하이브리드 RRF 병합
│   │   ├── embedding_client.py  # Ollama bge-m3 임베딩 클라이언트
│   │   ├── reranker.py          # Cross-encoder 리랭킹 (bge-reranker-v2-m3)
│   │   ├── conversation.py      # 인메모리 대화 세션 저장소
│   │   ├── query_rewriter.py    # LLM 기반 쿼리 재작성
│   │   ├── llm_client.py        # Ollama LLM 클라이언트
│   │   ├── settings_service.py  # settings.json CRUD, 런타임 적용
│   │   └── analytics.py         # 접속 통계 서비스
│   └── packages/          # 오프라인 설치용 wheel 파일
├── models/                 # 로컬 리랭커 모델 (bge-reranker-v2-m3)
├── backups/                # 문서 편집 백업 파일
├── tools/                  # 유틸리티 스크립트 및 변환기
│   ├── build-search-index.py  # 검색 인덱스 생성
│   ├── build-vector-index.py  # FAISS 벡터 인덱스 빌드
│   ├── html_to_text.py        # HTML→검색텍스트 (테이블→MD, MathML→LaTeX)
│   ├── excel-to-menu.py       # 엑셀 → menu.json 변환
│   ├── import-glossary.py     # CSV → glossary.json 변환
│   ├── create-admin.py        # CLI admin 계정 생성/관리
│   └── converter/             # 문서 변환기 (DOCX/PDF → HTML, COM 전처리 포함)
└── docs/                   # 문서
    ├── 01-QUICK-START.md
    ├── 02-INSTALLATION.md
    ├── 03-BACKEND-SETUP.md
    ├── 04-USER-GUIDE.md
    ├── ARCHITECTURE.md
    ├── RAG-PIPELINE.md
    ├── RAG-TECHNICAL-REPORT.md
    └── GIT-GUIDE.md
```

## 기술 스택

- **HTML5**: 문서 구조
- **CSS3**: 스타일링 (록히드마틴 스타일)
- **Vanilla JavaScript**: 동적 기능 (프레임워크 없음)
- **JSON**: 데이터 관리

## 시스템 요구사항

- **웹 서버**: Apache Tomcat 7.0 이상
- **브라우저**: Chrome, Edge, Firefox (최신 버전 권장)
- **Python**: 3.11 이상 (백엔드, 검색 인덱스 생성용)
- **FastAPI**: AI 채팅/문서 편집 백엔드 (선택사항)
- **Ollama**: AI 채팅 + 임베딩 기능 사용 시 필요 (선택사항)
- **faiss-cpu**: 벡터 검색 (선택사항, 하이브리드 검색 시 필요)
- **sentence-transformers**: Cross-encoder 리랭커 (선택사항, 검색 정밀도 향상)

## 주요 기능

### 1. 계층적 트리 메뉴
- JSON 파일 기반 동적 메뉴 생성
- 3단계 깊이 지원
- 현재 페이지 자동 하이라이트 및 경로 확장

### 2. 섹션 네비게이터
- 페이지 내 h1 ~ h6 자동 수집
- h2 단위 접기/펼치기 (하위 항목 독립 토글)
- 클릭으로 섹션 이동
- 스크롤 위치 추적 및 활성 섹션 자동 펼침/자동 스크롤

### 3. 콘텐츠 이미지 경로 자동 변환
- 콘텐츠 HTML 내 상대 경로 이미지를 자동으로 올바른 경로로 변환
- img, source, poster 속성 대상

### 4. 통합 검색
- 사전 인덱싱 방식의 빠른 검색
- 검색어 하이라이트
- 결과 미리보기

### 5. 패널 토글
- 좌측/우측 패널 숨기기/표시
- 콘텐츠 읽기에 집중 가능

### 6. 배너 슬라이드쇼
- 홈페이지 상단 이미지/영상 혼합 자동 전환 (4초 간격)
- Ken Burns 효과 (이미지 확대/이동 애니메이션)
- 마우스 호버 시 일시정지
- 점 네비게이션으로 수동 이동 가능

### 7. 홈페이지 섹션 링크
- menu.json 기반 자동 생성 (트리 메뉴 연동)
- 주요 카테고리로 빠른 이동
- 통계 스트립 (문서 수, 이미지 수, 용어 수 등)
- 깔끔한 3열 그리드 레이아웃

### 8. AI 채팅 (Ollama 기반)
- 문서 내용 기반 Q&A
- 로컬 LLM 사용 (에어갭 환경 호환)
- **하이브리드 검색**: 키워드 + 벡터 검색 RRF 병합 → Cross-encoder 리랭킹
- **멀티턴 대화**: 후속 질문 컨텍스트 유지, 세션 내 대화 기록 관리
- **구조 보존 검색**: 테이블/수식 데이터 기반 질문·답변 가능
- 스트리밍 응답 (실시간 타이핑 효과)
- 빠른 질문 버튼 (페이지 요약, 핵심 내용, 쉬운 설명)
- 마크다운 렌더링 지원

### 9. 다크/라이트 모드
- 해/달 아이콘으로 테마 전환
- 선택한 테마 localStorage 저장 (재방문 시 유지)
- 인쇄 시 라이트 색상 자동 적용

### 10. 북마크
- 헤딩(h1~h4) 호버 시 별표 아이콘으로 북마크 추가/제거
- 문서별 그룹핑 오버레이 목록
- 다른 문서 북마크 클릭 시 로드 후 섹션 이동
- localStorage 저장 (서버 불필요)

### 11. 키보드 단축키
- `?` : 단축키 도움말 모달 열기/닫기
- `/` 또는 `Ctrl+K` : 검색 열기
- `←` `→` : 이전/다음 문서 이동
- `H` : 홈으로 이동
- `B` : 북마크 열기
- `Esc` : 모달/오버레이 닫기

### 12. 항공 용어집
- 26,000+ 항공 용어(약어, 영문, 한국어) 검색 및 탐색
- A-Z 카드 그리드 + 알파벳 필터 + 실시간 검색
- 본문 약어 자동 인식: 문서 내 용어집 약어에 점선 밑줄 표시
- 약어 클릭 시 팝업으로 풀네임/한국어 해설 즉시 확인
- 통합 검색 연동: 문서 검색 결과에 용어집 매칭 결과 함께 표시
- CSV 기반 용어 관리 (`data/glossary.csv` → `tools/import-glossary.py`)

## 사용 방법

### 메뉴 추가

`data/menu.json` 파일 수정:

```json
{
  "label": "새로운 메뉴",
  "children": [
    {
      "label": "하위 항목",
      "url": "contents/new-page.html"
    }
  ]
}
```

### 콘텐츠 추가

1. `contents/` 폴더에 HTML 파일 생성
2. `data/menu.json`에 메뉴 항목 추가
3. 검색 인덱스 업데이트:

```bash
python tools/build-search-index.py
```

### Word 문서 변환

내장 변환기 사용 (권장):

```bash
# 내장 변환기로 변환 (캡션 ID + 참조 링크 자동 생성)
python tools/converter/converter.py input.docx -o contents/output/output.html
```

또는 웹 UI에서 직접 업로드하여 변환할 수도 있습니다 (백엔드 실행 필요).

자세한 내용은 [사용자 가이드](docs/04-USER-GUIDE.md)를 참조하세요.

### AI 채팅 설정

`js/config.js` 파일에서 Ollama 서버 주소와 모델을 설정합니다:

```javascript
const AI_CONFIG = {
    enabled: true,                          // false: 챗봇 아이콘 숨김
    useBackend: true,                       // true: 백엔드 모드 (권장)
    backendUrl: 'http://localhost:8000',    // 백엔드 서버 주소
    ollamaUrl: 'http://localhost:11434',    // 직접 호출 모드 시 Ollama 주소
    model: 'gemma3:4b',                     // 직접 호출 모드 시 모델
    maxContextLength: 8000,                 // 컨텍스트 최대 길이 (백엔드 기준)
    maxSearchResults: 5                     // 검색 결과 최대 개수
};

const DISPLAY_CONFIG = {
    platformName: 'WebBook',              // 플랫폼 이름 (고정)
    siteTitle: 'WebBook',                 // 사이트 타이틀 (관리자 설정 변경 가능)
    version: 'v5.5',
    tableStyle: 'bordered',
};
```

> **참고**: AI 채팅은 Ollama가 실행 중일 때만 사용 가능합니다. Ollama가 없어도 웹북의 다른 기능은 정상 작동합니다.

## 라이선스

이 템플릿은 KF-21 개발 프로그램을 위해 제작되었습니다.

## 지원

문제가 발생하거나 개선 사항이 있으면 웹북 관리자에게 문의하세요.

---

**WebBook v5.5** - 에어갭 환경을 위한 간편하고 강력한 AI 기술문서 포털 플랫폼
