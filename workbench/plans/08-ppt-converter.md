# PPT → HTML 변환기 계획서

> **작성일**: 2026-03-10
> **상태**: 계획 (미착수)
> **목적**: Explorer에서 PPT/PPTX 문서를 업로드·변환·탐색할 수 있도록 지원

---

## 1. 현황 분석

### 1-1. 현재 지원 포맷

| 포맷 | 변환기 | 산출물 |
|------|--------|--------|
| `.docx` | `tools/converter/converter.py` (DocxConverter) | 섹션별 `<h1>`~`<h6>` + 본문 HTML |
| `.pdf` | `tools/converter/pdf_converter.py` (PdfConverter) | TOC 기반 구조 복원 HTML |

- **업로드 API** (`backend/api/upload.py`): `.docx`, `.pdf`만 허용 (line 299-304)
- **최대 파일 크기**: 500 MB, 타임아웃: 600초

### 1-2. 업로드 → 탐색 전체 파이프라인

```
파일 업로드 (POST /upload)
  → 파일 검증 (.docx/.pdf, 500MB)
  → 변환기 선택 (확장자 기반)
  → HTML 변환 → contents/{경로}.html 저장
  → (선택) menu.json 갱신
  → (선택) 검색 인덱스 재구성 (build-search-index.py --inject-ids)
  → (선택) 벡터 인덱스 증분 추가 (FAISS append)
  → NDJSON 스트리밍 진행 이벤트 반환
```

### 1-3. Explorer 기능 의존성 분석

Explorer의 모든 핵심 기능은 **HTML 내 heading 태그(`<h1>`~`<h6>`)와 텍스트 콘텐츠**에 의존한다.

| 기능 | 의존 요소 | PPT 미지원 시 영향 |
|------|-----------|-------------------|
| 목차 (On This Page) | `<h1>`~`<h6>` heading 태그 | heading 없으면 목차 빈 패널 |
| 키워드 검색 | `search-index.json` 내 `content` 텍스트 | 텍스트 없으면 검색 불가 |
| AI 채팅 (RAG) | 벡터 인덱스 + 텍스트 컨텍스트 | 텍스트 없으면 RAG 컨텍스트 부재 |
| 북마크 | heading의 `id` 속성 | heading 없으면 북마크 불가 |
| 용어집 하이라이트 | 본문 텍스트 노드 순회 | 텍스트 없으면 하이라이트 불가 |
| 섹션 스크롤 네비게이션 | heading 기반 섹션 분할 | heading 없으면 네비게이션 불가 |

**결론**: PPT 변환 시 heading 구조 + 텍스트 콘텐츠 산출이 **필수**.

---

## 2. PPT 문서의 특성과 도전 과제

### 2-1. DOCX/PDF와의 근본적 차이

| 특성 | DOCX/PDF | PPT |
|------|----------|-----|
| 읽기 방향 | 세로 연속 스크롤 | 가로 슬라이드 단위 |
| 구조 | heading → 본문 계층 | 슬라이드 → 텍스트 박스 나열 |
| 레이아웃 | 선형 텍스트 흐름 | 자유 배치 (좌표 기반) |
| 반복 요소 | 없음 | 슬라이드 마스터 타이틀/로고 반복 |

### 2-2. PPT 변환 시 핵심 난제

1. **슬라이드 타이틀 반복**: 마스터/레이아웃에서 상속된 제목이 매 슬라이드마다 반복 → 중복 heading 대량 생성
2. **가로→세로 레이아웃 전환**: 16:9 비율 콘텐츠를 세로 문서로 재배치 시 가독성 저하
3. **자유 배치 텍스트**: 텍스트 박스 좌표 기반 배치 → 읽기 순서 결정 어려움
4. **시각 중심 콘텐츠**: 다이어그램, 차트, SmartArt 등 텍스트 추출 불가/부족
5. **구조 정보 부재**: PPT에는 heading level 개념이 없음 → 구조 추론 필요

---

## 3. 변환 전략: 슬라이드 이미지 + 히든 텍스트

### 3-1. 핵심 아이디어

```
각 슬라이드를 이미지로 렌더링 (시각적 충실도 보존)
+ 숨겨진 텍스트 레이어 (검색/RAG/목차용)
+ heading 구조 자동 생성 (Explorer 기능 호환)
```

### 3-2. 산출 HTML 구조

```html
<!-- 슬라이드 1 -->
<section id="slide-1">
  <h2>슬라이드 제목 텍스트</h2>
  <div class="slide-frame">
    <img src="{문서명}_images/slide_001.png" alt="Slide 1" decoding="async">
  </div>
  <div class="slide-text" aria-hidden="true" style="position:absolute;left:-9999px;">
    슬라이드 내 모든 텍스트 (텍스트 박스 순서대로)
  </div>
</section>

<!-- 슬라이드 2 -->
<section id="slide-2">
  <h2>다음 슬라이드 제목</h2>
  ...
</section>
```

### 3-3. 전략의 장점

| 항목 | 효과 |
|------|------|
| 시각적 충실도 | 슬라이드 이미지 = 원본 그대로 |
| 검색 | 히든 텍스트 → `html_to_text.py`가 추출 → 검색 인덱스 |
| RAG | 히든 텍스트 → 벡터 인덱스 → AI 채팅 컨텍스트 |
| 목차 | `<h2>` heading → On This Page 패널 자동 생성 |
| 북마크 | `id="slide-N"` → 북마크 및 링크 가능 |
| 스크롤 | 세로 나열된 슬라이드 이미지 → 자연스러운 스크롤 |
| 기존 코드 변경 | **없음** — 표준 HTML 산출이므로 파이프라인 호환 |

---

## 4. 기술 구현 설계

### 4-1. 의존성

| 도구 | 용도 | 비고 |
|------|------|------|
| `python-pptx` | PPTX 파싱, 텍스트/노트 추출 | pip install, 순수 Python |
| LibreOffice (headless) | 슬라이드 → PNG 이미지 변환 | `soffice --headless --convert-to png` |

- **python-pptx**: 텍스트 추출 전용 (이미지 렌더링 불가)
- **LibreOffice**: 이미지 렌더링 전용 (텍스트 구조 파싱 어려움)
- 두 도구의 조합이 최적

> **폐쇄망 고려**: 둘 다 오프라인 설치 가능. LibreOffice는 MSI/포터블 배포.

### 4-2. 변환기 클래스 설계

```
tools/converter/pptx_converter.py (신규)
```

```python
class PptxConverter:
    """PPTX → HTML 변환기"""

    def convert(self, input_path: str, output_path: str, **options) -> ConversionResult:
        """
        1. python-pptx로 PPTX 파싱
        2. 슬라이드별 텍스트/노트 추출
        3. LibreOffice headless로 슬라이드 → PNG 변환
        4. HTML 조립 (이미지 + 히든 텍스트 + heading)
        5. ConversionResult 반환
        """
```

### 4-3. 텍스트 추출 로직

```python
from pptx import Presentation
from pptx.util import Pt

def extract_slide_texts(pptx_path):
    prs = Presentation(pptx_path)
    slides = []

    for i, slide in enumerate(prs.slides):
        title = ""
        body_texts = []

        for shape in slide.shapes:
            if shape.has_text_frame:
                text = shape.text_frame.text.strip()
                if not text:
                    continue
                # 타이틀 플레이스홀더 감지
                if shape.is_placeholder and shape.placeholder_format.idx == 0:
                    title = text
                else:
                    body_texts.append(text)

            # 테이블 내 텍스트
            if shape.has_table:
                for row in shape.table.rows:
                    for cell in row.cells:
                        cell_text = cell.text.strip()
                        if cell_text:
                            body_texts.append(cell_text)

        # 발표자 노트
        notes = ""
        if slide.has_notes_slide:
            notes = slide.notes_slide.notes_text_frame.text.strip()

        slides.append({
            "index": i + 1,
            "title": title,
            "body": "\n".join(body_texts),
            "notes": notes
        })

    return slides
```

### 4-4. 슬라이드 이미지 생성

```python
import subprocess
import shutil
from pathlib import Path

def render_slides_to_images(pptx_path, output_dir):
    """LibreOffice headless로 PPTX → PNG 변환"""
    tmp_dir = Path(output_dir) / "_lo_tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    # LibreOffice는 전체 슬라이드를 개별 PNG로 출력
    subprocess.run([
        "soffice", "--headless", "--convert-to", "png",
        "--outdir", str(tmp_dir),
        str(pptx_path)
    ], check=True, timeout=300)

    # 출력 파일 정리 (slide_001.png, slide_002.png, ...)
    images = sorted(tmp_dir.glob("*.png"))
    result = []
    for i, img in enumerate(images):
        target = Path(output_dir) / f"slide_{i+1:03d}.png"
        shutil.move(str(img), str(target))
        result.append(target.name)

    tmp_dir.rmdir()
    return result
```

> **참고**: LibreOffice의 PNG 출력은 슬라이드당 1파일. `--convert-to png`는 멀티페이지 PPTX를 자동 분리.
> 실제 구현 시 LibreOffice 경로 탐지, 타임아웃 처리, 에러 핸들링 추가 필요.

### 4-5. HTML 조립

```python
def assemble_html(slides_data, image_files, doc_name):
    """슬라이드 데이터 + 이미지 → HTML 문서"""
    sections = []
    img_dir = f"{doc_name}_images"

    for slide, img_file in zip(slides_data, image_files):
        idx = slide["index"]
        title = slide["title"] or f"슬라이드 {idx}"
        body = slide["body"]
        notes = slide["notes"]

        # 히든 텍스트: 본문 + 노트 결합
        hidden_text = body
        if notes:
            hidden_text += f"\n[발표자 노트] {notes}"

        section_html = f'''<section id="slide-{idx}">
  <h2>{escape_html(title)}</h2>
  <div class="slide-frame">
    <img src="{img_dir}/{img_file}" alt="Slide {idx}" decoding="async">
  </div>
  <div class="slide-text" style="position:absolute;left:-9999px;overflow:hidden;">
    {escape_html(hidden_text)}
  </div>
</section>'''
        sections.append(section_html)

    return "\n\n".join(sections)
```

### 4-6. 타이틀 중복 제거

PPT 마스터 슬라이드에서 반복되는 제목 처리:

```python
def deduplicate_titles(slides_data):
    """연속 동일 타이틀 → 번호 접미사 또는 본문 첫 줄로 대체"""
    prev_title = None
    count = 0

    for slide in slides_data:
        if slide["title"] == prev_title:
            count += 1
            # 본문 첫 줄이 있으면 부제로 활용
            first_line = slide["body"].split("\n")[0].strip() if slide["body"] else ""
            if first_line and len(first_line) < 80:
                slide["title"] = f"{slide['title']} — {first_line}"
            else:
                slide["title"] = f"{slide['title']} ({count + 1})"
        else:
            prev_title = slide["title"]
            count = 0

    return slides_data
```

### 4-7. heading 레벨 추론

PPT에는 heading level이 없으므로 휴리스틱으로 추론:

| 조건 | 추론 레벨 |
|------|-----------|
| 첫 슬라이드 (표지) | `<h1>` (문서 제목) |
| 섹션 구분 슬라이드 (본문 없이 타이틀만) | `<h2>` (대분류) |
| 일반 슬라이드 | `<h3>` (소분류) |

```python
def infer_heading_levels(slides_data):
    for i, slide in enumerate(slides_data):
        if i == 0:
            slide["heading_level"] = 1  # 표지
        elif not slide["body"].strip():
            slide["heading_level"] = 2  # 섹션 구분
        else:
            slide["heading_level"] = 3  # 일반 콘텐츠
    return slides_data
```

---

## 5. 파이프라인 통합

### 5-1. 업로드 API 변경

**`backend/api/upload.py`**

```python
# 허용 확장자 추가
ALLOWED_EXTENSIONS = {".docx", ".pdf", ".pptx"}  # .pptx 추가

# run_converter() 분기 추가
async def run_converter(temp_path, target_path, ext, ...):
    if ext == ".docx":
        # 기존 DocxConverter
    elif ext == ".pdf":
        # 기존 PdfConverter
    elif ext == ".pptx":
        from tools.converter.pptx_converter import PptxConverter
        converter = PptxConverter()
        result = converter.convert(str(temp_path), str(target_path))
        return result
```

### 5-2. 이후 파이프라인 — 변경 없음

변환기가 표준 HTML을 산출하므로:

- ✅ `build-search-index.py`: heading 태그 파싱 → 섹션 분할 → 그대로 동작
- ✅ `html_to_text.py`: 태그 제거 → 텍스트 추출 → 그대로 동작 (히든 텍스트 포함)
- ✅ FAISS 벡터 인덱스: search-index.json 기반 → 그대로 동작
- ✅ `menu.json` 갱신: URL 매핑 → 그대로 동작
- ✅ Explorer 모든 기능: heading + 텍스트 기반 → 그대로 동작

### 5-3. CSS 추가 (선택)

슬라이드 이미지 표시를 위한 최소 스타일:

```css
/* content.css에 추가 */
.slide-frame {
    max-width: 100%;
    margin: 1rem 0;
    text-align: center;
}

.slide-frame img {
    max-width: 100%;
    height: auto;
    border: 1px solid var(--border-color);
    border-radius: var(--radius-md);
    box-shadow: var(--shadow-sm);
}
```

---

## 6. 기능 호환성 매트릭스

| Explorer 기능 | DOCX | PDF | PPT (이 계획) | 비고 |
|---------------|------|-----|---------------|------|
| 문서 표시 | ✅ 원문 HTML | ✅ 원문 HTML | ✅ 슬라이드 이미지 | |
| 목차 (On This Page) | ✅ heading 기반 | ✅ heading 기반 | ✅ 슬라이드별 heading | |
| 키워드 검색 | ✅ 전체 텍스트 | ✅ 전체 텍스트 | ✅ 히든 텍스트 | |
| AI 채팅 (RAG) | ✅ 섹션 컨텍스트 | ✅ 섹션 컨텍스트 | ✅ 슬라이드별 텍스트 | |
| 북마크 | ✅ heading id | ✅ heading id | ✅ slide-N id | |
| 용어집 하이라이트 | ✅ 텍스트 노드 | ✅ 텍스트 노드 | ⚠️ 히든 텍스트만 | 이미지 위 불가 |
| 섹션 스크롤 | ✅ heading 간 이동 | ✅ heading 간 이동 | ✅ 슬라이드 간 이동 | |

**⚠️ 제한사항**: 용어집 하이라이트는 이미지 위에 오버레이 불가. 히든 텍스트에서는 매칭되나 시각적 강조 없음. 실용적으로는 검색→슬라이드 이동으로 대체 가능.

---

## 7. 구현 단계

### Phase 1: 핵심 변환기 (필수)

- [ ] `tools/converter/pptx_converter.py` 신규 작성
  - python-pptx 텍스트 추출
  - LibreOffice headless 이미지 렌더링
  - HTML 조립 (이미지 + 히든 텍스트 + heading)
  - 타이틀 중복 제거
  - heading 레벨 추론
- [ ] `tools/converter/config.json`에 PPT 옵션 추가
- [ ] `ConversionResult` 통계에 슬라이드 수 항목 추가

### Phase 2: 업로드 통합

- [ ] `backend/api/upload.py` 허용 확장자에 `.pptx` 추가
- [ ] `run_converter()` 분기에 PptxConverter 추가
- [ ] 업로드 UI 안내 텍스트에 `.pptx` 추가

### Phase 3: 스타일링

- [ ] `css/content.css`에 `.slide-frame` 스타일 추가
- [ ] 라이트/다크모드 양쪽 확인

### Phase 4: 테스트 및 검증

- [ ] 다양한 PPT 파일 테스트 (텍스트 중심, 이미지 중심, 차트 포함)
- [ ] 검색 인덱스 정상 생성 확인
- [ ] RAG 질의 응답 품질 확인
- [ ] 목차/북마크/스크롤 동작 확인

---

## 8. 제약 및 리스크

| 리스크 | 영향 | 완화 |
|--------|------|------|
| LibreOffice 미설치 환경 | 이미지 렌더링 불가 | 설치 가이드 제공, 텍스트 전용 폴백 모드 |
| 대용량 PPT (100+ 슬라이드) | 변환 시간/이미지 용량 | 이미지 해상도 옵션 (DPI 조절), 진행률 표시 |
| SmartArt/차트 텍스트 | python-pptx로 추출 어려움 | LibreOffice가 이미지에 포함, 텍스트는 부분 손실 |
| `.ppt` (레거시 바이너리) | python-pptx 미지원 | LibreOffice로 `.pptx` 사전 변환 또는 미지원 안내 |
| 폐쇄망 LibreOffice 배포 | 설치 파일 반입 필요 | 포터블 빌드 또는 MSI 오프라인 설치 |

---

## 9. 향후 확장 가능성

- **이미지 위 텍스트 오버레이**: 좌표 기반 반투명 텍스트 → 용어집 하이라이트 지원
- **슬라이드 썸네일 네비게이션**: 좌측 트리에 슬라이드 썸네일 표시
- **발표자 노트 토글**: 노트를 접을 수 있는 패널로 표시
- **애니메이션/전환 무시**: 정적 변환이므로 애니메이션 정보는 버림 (적절한 판단)
