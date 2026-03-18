# Translator 품질 향상 + 웹 뷰 계획서

> 작성일: 2026-03-17
> 최종 갱신: 2026-03-17
> 상태: Phase 1 완료 / Phase 2 미착수

---

## 목적

Translator 시스템의 핵심 사용자 여정에서 **마찰을 제거**하고(Phase 1~4),
번역 결과를 **웹 콘텐츠로 활용**할 수 있는 새로운 뷰 모드를 추가한다(Phase 5).

## 배경

### 사용자 피드백
- 테스트 참여 동료들이 Translator를 **개인 문서 저장소 / 지식 저장소**로 사용하고 싶다고 요청
- 논문은 레이아웃 보존 번역이 필요하지만, 세미나 자료·외부 문서는 **탐색 가능한 형태**로 저장하고 싶음
- 향후 챗봇 연계를 통한 **개인 지식 도우미** 활용 요구
- 이는 NotebookLM, Notion, Readwise Reader 등 **문서 중심 지식 관리 도구**의 방향과 일치

### 현재 번역 엔진의 역할 구분
| 엔진 | 목적 | 출력 |
|------|------|------|
| **pdf2zh (PDF 엔진)** | 레이아웃 보존 번역 (논문, 인쇄/제출용) | PDF |
| **텍스트 엔진** | PDF 품질 문제 우회 (겹침, 인코딩 깨짐) | PDF (재조립) |
| **웹 뷰 (신규)** | 읽기/검토/탐색 최적화, 지식 저장소 활용 | HTML |

텍스트 엔진의 PDF 재조립은 원본과 시각적으로 상이하며, DRM 이슈도 있음.
웹 뷰는 기존 텍스트 엔진이 이미 추출하는 데이터(레이아웃 블록, 번역 텍스트, 이미지 캡처)를 **PDF 대신 HTML로 출력**하는 방식.

## 현황 진단

| 마찰 지점 | 현재 | 목표 |
|-----------|------|------|
| 원문 탐색 | DPR 미대응 → 고해상도 디스플레이에서 흐릿 | HiDPI 선명 렌더링 |
| 번역 결과 | 페이지별 독립 번역 → 용어 불일관, 문장 끊김 | 용어집 + 페이지 경계 문맥 전달 |
| 결과 활용 | PDF만 존재, 다운로드 불가 → DRM 적용 시 결과 유실 | PDF 다운로드 + 텍스트 내보내기 |
| 결과 형태 | PDF 고정 → 편집/검색/다크모드 불가 | 웹 뷰 옵션 (HTML) |

## 핵심 원칙

1. **업계 표준 방식 우선** — PDF.js HiDPI 공식 패턴, CAT 도구 용어집 방식 등 검증된 접근법 채택
2. **기존 코드 최소 변경** — 새 모듈 추가 > 기존 코드 대폭 수정
3. **단계별 검증** — 각 Phase 완료 후 동작 확인, 이전 기능 회귀 없는지 점검
4. **롤백 가능** — 각 Phase는 독립적. 문제 발생 시 해당 Phase만 되돌릴 수 있도록 설계
5. **기존 엔진 유지** — 웹 뷰는 세 번째 옵션으로 추가. 기존 PDF/텍스트 엔진 제거하지 않음

## 설계 결정 기록

| 결정 | 근거 |
|------|------|
| 전체 번역 큐 미도입 | 10페이지에 20~30분 소요. 전체 번역은 GPU 장시간 점유 + 사용자 대기 고통. 페이지별 온디맨드가 이 환경에서 올바른 설계. 기존에 전체→페이지→범위(5p)로 진화한 이력 존재 |
| 번역 캐시 미도입 | 학술 논문에서 페이지 간 동일 텍스트 블록 반복 빈도 낮음. 캐시 무효화(용어집·모델 변경) 복잡도 대비 GPU 절감 효과 미미 |
| 용어집 범위: 유저별 단일 | 개인 작업공간 컨셉에 부합. 폐쇄망 소규모 팀이므로 조직 공용 필요성 낮음. 추후 관리자 공용 계층 확장 가능 |
| 대역 DOCX 내보내기 보류 | PDF 다운로드 + TXT로 핵심 요구 충족. DOCX는 실사용 요구 확인 후 |
| 웹 뷰는 세 번째 옵션(B안) | 기존 텍스트 엔진을 교체(A안)하지 않고 추가. PDF→HTML 품질이 문서마다 다를 수 있으므로, 품질 불충분 시 기존 모드로 폴백 가능해야 함. 레이아웃 비교 롤백 전례를 반복하지 않기 위한 안전 장치 |
| 웹 뷰에 편집기 미포함 (초기) | 변환 품질을 실사용으로 먼저 검증. 편집기를 처음부터 넣으면 변환 품질 문제를 사용자 수동 교정으로 떠넘기는 구조가 됨. 품질 검증 후 편집기 추가 여부 판단 |
| 웹 뷰에서 스크롤 동기화 비활성화 | PDF(페이지 기반)와 HTML(연속 흐름)의 스크롤 동기화는 본질적으로 불일치. 대신 클릭→네비게이션(박스 하이라이트) 방식 채택. 기존 마킹/AI 채팅 섹션 네비게이션 패턴 재활용 |

---

## 실행 계획

### Phase 1: PDF 렌더링 HiDPI 대응

> PDF.js 공식 문서 권장 패턴. 캔버스 내부 해상도를 물리 픽셀에 맞추고, CSS로 논리 크기 유지.

- ✅ **1-1. 좌측 패널 (renderLeftPage) DPR 적용**
  - 대상: `js/translator.js:504` (`renderLeftPage` 내부)
  - `devicePixelRatio` 기반 canvas 내부 해상도 확대 + `ctx.setTransform(dpr, 0, 0, dpr, 0, 0)`
  - 텍스트 레이어, 어노테이션 레이어, 마킹(% 좌표)에 영향 없음 확인

- ✅ **1-2. 우측 패널 (renderRightPage) DPR 적용**
  - 대상: `js/translator.js:733` (`renderRightPage` 내부)
  - 동일 패턴 적용

- ✅ **1-3. 검증**
  - DPR 1.125 환경에서 정상 렌더링 확인 (브라우저 새로고침으로 즉시 적용)
  - DPR 1.0에서는 `Math.floor(width * 1) = width`로 기존과 동일 동작
  - 마킹/스크롤 동기화/줌 기능 회귀 없음

- **예상 공수**: 0.5일
- **리스크**: 매우 낮음. PDF.js 표준 패턴이며, DOM 레이어에 영향 없음
- **안정성 근거**: Canvas HiDPI는 MDN Web Docs에서 권장하는 표준 기법. PDF.js 공식 예제에서도 동일 패턴 사용

---

### Phase 2: 용어집 (Glossary)

> CAT 도구(MateCat, SDL Trados, MemoQ)에서 30년 이상 사용된 업계 표준 기능.
> 번역 프롬프트에 용어 목록을 주입하여 일관된 번역을 유도한다.

**범위**: 유저별 단일 용어집. 개인 작업공간 컨셉에 부합하며, 추후 관리자 공용 계층 확장 가능.

**사전 조사 결과 (2026-03-19)**:
- pdf2zh(babeldoc)는 `--glossaries` CSV 플래그를 공식 지원 (CSV 포맷: `source,target,tgt_lng`)
- babeldoc 내부에서 hyperscan 매칭 → 해당 페이지에 등장하는 용어만 필터링 → LLM 프롬프트에 용어 테이블 자동 주입 (텍스트 치환이 아닌 프롬프트 방식)
- **자동 용어 추출(AutomaticTermExtractor)이 기본 활성화** — 전체 처리 시간의 ~30% 차지 (DeepWiki 분석). `--no-auto-extract-glossary`로 비활성화 가능
- GitHub Issue #995: 개발자가 "용어집 기능은 아직 디버깅 단계"라고 인정. 전역 적용 안 되는 버그 보고됨
- 실사용 사례/블로그가 매우 적음 (기능이 새롭기 때문)
- LLM 프롬프트 지시 방식이므로 LLM이 100% 따르지 않을 수 있음 (특히 잘 알려진 약어)

**진행 전략**: Step별 분리 검증. UI 먼저 완성 → pdf2zh 연동 → 텍스트 엔진 연동

- ⬜ **2-0. 기준선 확인 (착수 전)**
  - 현재 원본 코드 상태에서 동일 문서 동일 페이지 번역 → 정상 동작/속도 기준선 확보
  - `--no-auto-extract-glossary`를 용어집 유무와 관계없이 항상 추가하여 기본 속도 개선 (기존에도 불필요한 LLM 호출 발생 중)

- ⬜ **2-1. 용어집 데이터 구조**
  - JSON 저장: `data/translator/{username}/_glossary.json`
    ```json
    {
      "version": 1,
      "entries": [
        { "source": "availability", "target": "가용성" },
        { "source": "latency", "target": "지연시간" }
      ]
    }
    ```
  - CSV 동기 생성: `data/translator/{username}/_glossary.csv` (pdf2zh `--glossaries`용)
    ```csv
    source,target
    availability,가용성
    latency,지연시간
    ```

- ⬜ **2-2. 백엔드 API**
  - `GET /api/translator/glossary` — 용어집 조회
  - `PUT /api/translator/glossary` — 용어집 저장 (전체 교체). **`Request.json()` 사용** (`Body(...)` 파싱 오류 회피)
  - 인증: `get_current_user` 필수

- ⬜ **2-3. 프론트엔드 UI** (번역 엔진 미연결 상태로 먼저 완성)
  - translator.html에 `toast.css`, `modal.css` 로드 추가 (CLAUDE.md CSS 로드 순서 준수)
  - 뷰어 툴바에 "용어집" 버튼 추가 (모델 선택 좌측, spacer 직후)
  - 클릭 시 모달 (`.modal-overlay` + `.modal-box` 패턴): 용어 목록 테이블 + 추가/삭제
  - Enter 키 지원, 중복 시 덮어쓰기, 오버레이 클릭 닫기
  - 이 단계에서 번역에는 영향 없음 → UI 저장/조회 동작만 검증

- ⬜ **2-4. pdf2zh 엔진 연동**
  - `translator_service.py`의 pdf2zh 명령에 추가:
    - `--no-auto-extract-glossary` — **항상 추가** (용어집 유무 무관, 기본 30% 속도 개선)
    - `--glossaries {csv_path}` — 용어집 CSV가 존재하고 내용이 있을 때만 추가
  - babeldoc이 자체적으로 해당 페이지 용어 필터링 + 프롬프트 주입 처리
  - 번역 테스트 → 기준선 대비 속도/품질 비교

- ⬜ **2-5. 텍스트 엔진 연동**
  - `text_translator.py`의 `_translate_text_ollama`에 `glossary_entries` 파라미터 추가
  - 시스템 프롬프트에 용어 테이블 삽입 (babeldoc과 유사 포맷):
    ```
    ## Glossary
    Always use the glossary's Target Term for any occurrence of its Source Term.
    | Source Term | Target Term |
    |-------------|-------------|
    | availability | 가용성 |
    ```
  - `translator_service.py`에서 페이지 텍스트 기반 용어 필터링 후 전달
  - 번역 테스트

- ⬜ **2-6. 검증**
  - 용어집 있을 때/없을 때 번역 결과 비교
  - `--no-auto-extract-glossary` 적용 전후 속도 비교
  - 용어가 실제 번역에 반영되는지 확인 (LLM이 무시하는 경우 허용 — 프롬프트 방식의 한계)
  - 모달 UI에서 추가/삭제 → 모달 재오픈 시 유지 확인

- **예상 공수**: 2~3일
- **리스크**: 중간. babeldoc 용어집이 "디버깅 단계"이므로 pdf2zh 측 적용이 불완전할 수 있음. 텍스트 엔진은 자체 구현이라 안정적.
- **안정성 근거**: `--glossaries` CSV는 pdf2zh 공식 플래그. 프롬프트 기반 용어 제어는 DeepL Glossary, Google Cloud Translation Glossary와 동일 원리. `--no-auto-extract-glossary`는 기존 불필요 오버헤드 제거로 오히려 안정성 향상.
- **참고 소스**: [pdf2zh 공식 문서](https://pdf2zh-next.com/advanced/advanced.html), [BabelDOC DeepWiki](https://deepwiki.com/funstory-ai/BabelDOC), [GitHub Issue #995](https://github.com/PDFMathTranslate/PDFMathTranslate/issues/995)

---

### Phase 3: 페이지 경계 문맥 전달

> 페이지별 독립 번역의 최대 약점인 "문장 단절"을 해소한다.
> 번역 대상 페이지 앞뒤의 텍스트를 컨텍스트로 함께 전송하되, 번역 범위는 해당 페이지만으로 한정한다.

- ⬜ **3-1. 백엔드: 인접 페이지 텍스트 추출**
  - `translator_service.py`에서 번역 시작 시 이전 페이지 마지막 3문장 + 다음 페이지 첫 3문장을 PyMuPDF로 추출
  - 추출된 텍스트를 컨텍스트 변수로 전달

- ⬜ **3-2. 텍스트 엔진 적용**
  - `text_translator.py`의 Ollama 호출 시 시스템 프롬프트에 컨텍스트 추가:
    ```
    [이전 페이지 끝]
    {prev_context}

    [번역 대상 - 이 부분만 번역하세요]
    {current_page_text}

    [다음 페이지 시작]
    {next_context}
    ```
  - 컨텍스트는 번역하지 않고 참조용으로만 사용됨을 프롬프트에 명시

- ⬜ **3-3. pdf2zh 엔진 적용 가능성 검토**
  - pdf2zh는 CLI 호출이므로 직접 컨텍스트 주입이 어려울 수 있음
  - 옵션 1: pdf2zh `--prompt` 플래그에 컨텍스트 포함 (Phase 2에서 지원 여부 확인됨)
  - 옵션 2: 미지원 시 텍스트 엔진에서만 적용 (pdf2zh는 자체적으로 문서 구조를 어느 정도 파악함)
  - **Phase 2의 pdf2zh 프롬프트 지원 여부 조사 결과에 따라 결정**

- ⬜ **3-4. 검증**
  - 페이지 경계에 걸치는 문장이 포함된 PDF로 테스트
  - 1페이지(이전 없음), 마지막 페이지(다음 없음) 정상 처리
  - 컨텍스트가 번역 결과에 섞이지 않는지 확인

- **예상 공수**: 2~3일
- **리스크**: 중간. pdf2zh 적용 가능성이 불확실. 텍스트 엔진은 확실히 적용 가능.
- **안정성 근거**: 문서 레벨 번역 컨텍스트 전달은 Google Document AI Translation, DeepL Document Translator에서 사용하는 표준 접근법

---

### Phase 4: 다운로드 + 텍스트 내보내기

> 번역 결과를 DRM 적용 전에 확보하고, 편집 가능한 형태로도 추출한다.
> 환경 특성상 PDF는 일정 시간 후 DRM이 적용되므로, 번역 완료 시점에 다운로드할 수 있어야 한다.

- ⬜ **4-1. PDF 다운로드**
  - 뷰어 툴바에 다운로드 버튼 (드롭다운)
    - "원본 PDF 다운로드" — `GET /api/translator/pdf/{doc_id}` + `Content-Disposition: attachment`
    - "현재 페이지 번역 PDF 다운로드" — 현재 보고 있는 번역 PDF 1페이지
    - "번역 PDF 전체 다운로드" — 번역 완료된 페이지만 병합한 PDF
  - 백엔드: 병합은 PyMuPDF `fitz.open()` + `insert_pdf()`로 구현 (기존 의존성 활용)
  - 미번역 페이지 처리: 병합 시 제외하거나, 원본 페이지로 대체 (사용자 선택)

- ⬜ **4-2. 텍스트 내보내기**
  - `GET /api/translator/export/{doc_id}?format=txt` — 번역 텍스트 (페이지별 구분)
  - `GET /api/translator/export/{doc_id}?format=bilingual-txt` — 원문/번역 병렬 텍스트
  - 소스: 텍스트 엔진은 mapping_blocks 활용, pdf2zh는 번역 PDF에서 PyMuPDF 텍스트 재추출
  - 미번역 페이지: "[페이지 N - 미번역]" 표시

- ⬜ **4-3. 프론트엔드 UI**
  - 뷰어 툴바에 다운로드 아이콘 버튼 + 드롭다운 메뉴
  - 옵션: 원본 PDF / 번역 PDF (현재 페이지) / 번역 PDF (전체 병합) / 번역 텍스트 / 대역 텍스트

- ⬜ **4-4. 검증**
  - 부분 번역 문서(일부 페이지만 완료)에서 다운로드 정상 동작
  - 병합 PDF 페이지 순서, 품질 확인
  - 100+ 페이지 문서 병합 성능 확인
  - 다운로드한 PDF가 정상 열리는지 확인

- **예상 공수**: 1.5~2일
- **리스크**: 낮음. PyMuPDF PDF 병합과 텍스트 추출은 검증된 작업
- **안정성 근거**: PDF 병합은 PyMuPDF 핵심 기능. 텍스트 내보내기는 단순 추출

---

### Phase 5: 웹 뷰 모드

> 번역 결과를 PDF가 아닌 **HTML 웹 콘텐츠**로 표시하는 세 번째 뷰 모드.
> 기존 텍스트 엔진이 추출하는 데이터(레이아웃 블록, 번역 텍스트, 이미지 캡처)를 PDF 대신 HTML로 출력한다.
> 기존 PDF/텍스트 엔진은 유지하고, 웹 뷰를 **추가 옵션**으로 제공한다.

#### 도입 근거
- **DRM 무관**: HTML은 DRM 적용 대상이 아님
- **편집 가능성**: 향후 contenteditable 또는 편집기 연동 가능 (이 단계에서는 미포함)
- **탐색 최적화**: 네이티브 검색(Ctrl+F), 복사/붙여넣기, 다크모드 자동 적용
- **지식 저장소 방향**: 웹 콘텐츠는 향후 RAG 인덱싱, 챗봇 연계의 자연스러운 입력
- **업계 트렌드**: arXiv HTML (2023~), Semantic Scholar Reader, Readwise 등 PDF→웹 전환 가속

#### 엔진 옵션 변경

현재: `PDF | 텍스트` (2종)
변경: `PDF | 텍스트 | 웹 뷰` (3종)

| 모드 | 좌측 패널 | 우측 패널 | 스크롤 동기화 | 용도 |
|------|-----------|-----------|-------------|------|
| PDF | 원문 PDF | 번역 PDF (pdf2zh) | O (기존) | 레이아웃 보존, 인쇄/제출 |
| 텍스트 | 원문 PDF | 번역 PDF (재조립) | O (기존) | PDF 품질 문제 우회 |
| **웹 뷰** | 원문 PDF | **번역 HTML** | **X → 클릭 네비게이션** | 읽기/검토/탐색, 지식 저장소 |

#### 구현

- ⬜ **5-1. 백엔드: HTML 생성**
  - `text_translator.py`의 기존 `_build_translated_pdf()` 로직을 참조하여 `_build_translated_html()` 추가
  - 입력: 기존 `mapping_blocks` (source_text, target_text, block_type, bbox, captured_image)
  - 출력: `pages/{N}/translated.html`
  - 블록 순서: y좌표 위→아래 (원문과 동일한 의미적 순서)
  - 텍스트 블록 (title, plain text): `<h2>`, `<p>` 등 시맨틱 HTML, 각 블록에 `data-block-id` 부여
  - 캡처 블록 (figure, table, formula): `<img>` 또는 `<figure>` 태그로 해당 문단 위치에 삽입
  - 수식: 가능하면 MathML로 변환 (Explorer의 `omml_to_mathml.py` 패턴 참조), 불가 시 이미지 유지
  - 스타일: `tokens.css` 변수 참조, 다크모드 자동 대응

- ⬜ **5-2. 백엔드: API**
  - `GET /api/translator/web-view/{doc_id}/page/{page_num}` — 페이지별 HTML 서빙
  - `POST /api/translator/web-translate/{doc_id}/page/{page_num}` — 웹 뷰용 번역 시작 → 202
  - `GET /api/translator/web-translate/{doc_id}/page/{page_num}/status` — 상태 조회
  - 내부적으로 텍스트 엔진의 번역 로직을 공유하되, 최종 출력만 HTML로 분기

- ⬜ **5-3. 프론트엔드: 엔진 토글 확장**
  - 기존 `translateEngine = 'pdf' | 'text'` → `'pdf' | 'text' | 'web'` 확장
  - 우측 패널: `web` 모드일 때 canvas 대신 `<div>` 컨테이너에 HTML 삽입
  - 스크롤 동기화: `web` 모드에서 비활성화
  - 폰트 스케일: CSS `font-size` 조절로 자연스럽게 동작

- ⬜ **5-4. 프론트엔드: 클릭 네비게이션**
  - 원문 PDF 텍스트 레이어 클릭 → 해당 영역의 블록 ID 식별 → 우측 HTML에서 같은 `data-block-id` 요소로 스크롤 + 하이라이트 플래시
  - 우측 HTML 블록 클릭 → 좌측 PDF에서 해당 bbox 영역으로 스크롤 + 박스 하이라이트
  - 기존 마킹 시스템의 `scrollIntoView` + 하이라이트 패턴 재활용

- ⬜ **5-5. 검증**
  - 다양한 PDF 유형으로 HTML 출력 품질 확인 (단순 논문, 다단 레이아웃, 표 많은 문서, 수식 문서)
  - 클릭 네비게이션 정확도 확인
  - 다크모드 전환 시 정상 표시
  - 기존 PDF/텍스트 모드에 영향 없는지 회귀 테스트
  - 웹 뷰 HTML의 네이티브 검색(Ctrl+F) 동작 확인

- **예상 공수**: 5~7일
- **리스크**: 중간. PDF→HTML 변환 품질이 문서마다 다를 수 있음. 기존 엔진 유지로 리스크 완화.
- **안정성 근거**: 텍스트 엔진의 기존 데이터 파이프라인 재활용. HTML 출력은 PDF 재조립보다 오히려 단순. arXiv HTML, Semantic Scholar Reader가 같은 방향을 검증함.

---

## 착수 순서

| 순서 | 항목 | Phase | 예상 공수 | 근거 |
|------|------|-------|----------|------|
| ~~1st~~ | ~~PDF HiDPI 렌더링~~ | ~~Phase 1~~ | ~~0.5일~~ | ✅ 완료 |
| 2nd | 용어집 | Phase 2 | 2일 | 번역 품질 향상의 핵심. Phase 3의 기반 (pdf2zh 프롬프트 지원 여부 확인) |
| 3rd | 페이지 경계 문맥 | Phase 3 | 2~3일 | 현재 가장 눈에 띄는 품질 문제 해소 |
| 4th | 다운로드 + 내보내기 | Phase 4 | 1.5~2일 | DRM 전 결과물 확보 |
| 5th | 웹 뷰 모드 | Phase 5 | 5~7일 | Phase 1~4 안정화 후 착수. 실사용 피드백 기반으로 범위 조정 가능 |

**Phase 1~4 합계**: 6~7.5일
**Phase 5 포함 합계**: 11~14.5일

---

## 보류 항목

| 항목 | 보류 근거 | 재검토 시점 |
|------|----------|------------|
| 웹 뷰 편집기 | Phase 5 HTML 품질을 실사용으로 먼저 검증. 편집기 없이 읽기 전용으로 시작 | Phase 5 사용 피드백 수집 후 |
| 대역 DOCX 내보내기 | PDF 다운로드 + TXT로 핵심 요구 충족. DOCX는 실사용 요구 확인 후 | Phase 4 사용 피드백 후 |
| 관리자 공용 용어집 | 유저별 용어집으로 시작. 팀 공유 요구가 실제 발생하면 추가 | 유저별 용어집 운용 경험 축적 후 |
| CSV 용어집 가져오기 | UI 직접 입력으로 충분. 대량 가져오기는 나중에 | 용어집 100개+ 규모 발생 시 |
| 번역 캐시 | 학술 논문 페이지 간 텍스트 중복 빈도 낮음. 무효화 복잡도 대비 효과 미미 | GPU 비용이 실제 문제될 때 |
| 전체 번역 큐 | 10페이지 20~30분 소요. 전체→페이지→범위(5p)로 진화한 이력. 페이지별 온디맨드가 올바른 설계 | GPU 성능 대폭 향상 시 |
| 텍스트 엔진 PE (인라인 편집) | Phase 4 내보내기 + Phase 5 웹 뷰로 편집 경로 먼저 검증 | Phase 5 사용 피드백 수집 후 |
| 번역 품질 신뢰도 표시 | LLM 자기 평가 정확도 낮음. 실용성 불확실 | 더 나은 QE 방법론 등장 시 |
| Explorer RAG 연계 | Translator 검색 인덱스를 Explorer RAG 파이프라인과 공유하여 챗봇에서 번역 문서 검색 가능. 별도 챗봇 구축보다 효율적 | Phase 5 웹 뷰 안정화 후, 플랫폼 구조 재설계(Plan 18) 시 검토 |
| 플랫폼 구조 재설계 | Explorer/Translator/Compare의 문서 중심 통합. 현재 기능 중심 분리에서 문서 중심 아키텍처로 전환 검토 | Phase 1~5 실사용 경험 + 사용자 피드백 축적 후 별도 계획서(Plan 18)로 설계 |

---

## 참고

### 업계 표준 참조

| 기능 | 참조 도구/표준 | 본 계획 적용 방식 |
|------|--------------|-----------------|
| HiDPI 렌더링 | PDF.js 공식 예제, MDN Canvas HiDPI | `devicePixelRatio` × canvas 해상도 |
| 용어집 | DeepL Glossary, Google Cloud Translation Glossary | JSON 용어 사전 + 프롬프트 주입 |
| 문맥 전달 | Google Document AI, DeepL Document Translator | 인접 페이지 텍스트를 시스템 프롬프트로 전달 |
| PDF 다운로드/병합 | PyMuPDF 공식 문서 | `fitz.open()` + `insert_pdf()` |
| 웹 뷰 (PDF→HTML) | arXiv HTML, Semantic Scholar Reader, Readwise | 레이아웃 블록 → 시맨틱 HTML |
| 클릭 네비게이션 | MateCat, MemoQ 세그먼트 연동 | `data-block-id` 기반 양방향 스크롤 + 하이라이트 |

### 향후 방향 (Plan 18 입력)

사용자 피드백에서 확인된 요구:
- Translator를 **개인 지식 저장소**로 활용하고 싶음 (논문 + 세미나 자료 + 외부 문서)
- **챗봇 연계**를 통한 개인 지식 도우미
- Explorer/Translator/Compare가 **문서 중심으로 통합**되길 기대
- 외부 인터넷 서비스(NotebookLM, Notion)와 유사한 경험 기대

이 요구들은 Plan 16 범위를 넘으며, 플랫폼 전체 아키텍처 결정이 필요. Phase 1~5 실사용 데이터가 쌓인 후 Plan 18에서 다룸.
