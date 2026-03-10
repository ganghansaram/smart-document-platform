# 폴백 번역 모드 — 자체 렌더링 엔진 설계

## 1. 배경 및 목적

### 문제
pdf2zh(BabelDOC)는 스캔 PDF, 복잡한 레이아웃, 특수 폰트 등에서 번역 결과가 깨진다.
특히 스캔 PDF는 원본 이미지 텍스트 위에 번역이 겹치는 근본적 한계가 있다.
메인테이너도 "스캔 PDF는 의도된 사용 사례가 아님"이라 명시.

### 목적
- 기존 번역 버튼(`이 페이지 번역`, `범위 번역`)을 **공유**하되, 엔진 선택 라디오버튼 추가
- `PDF 번역` (기존 pdf2zh): 레이아웃 보존 PDF 번역
- `텍스트 번역` (신규 자체 엔진): PyMuPDF 기반 자체 렌더링, 어떤 PDF든 안정적 번역

---

## 2. 레퍼런스 프로젝트 분석

### 핵심 참고 대상

| 프로젝트 | 핵심 기법 | 채택 여부 |
|---------|----------|----------|
| **PyMuPDF 공식 패턴** | `get_text("dict")` → `draw_rect(WHITE)` → `insert_htmlbox()` | **핵심 채택** |
| **BabelDOC DocLayout-YOLO** | ONNX 모델 (71.8MB), title/text/figure/table/formula 10클래스 감지 | **핵심 채택** (이미 설치됨) |
| **HIN_EN_PDF_Translator** | Hybrid Block Mode (X-gap 감지로 컬럼/표 자동 분리), IoU 스타일 매칭 | **폴백 참고** (YOLO 실패 시) |
| **fuba/pdf-translator** | PyMuPDF + HTML 출력, 이미지/표 원본 위치 보존 | **구조 참고** |
| **DeepL** | 계층적 제약조건 폰트 사이징 (페이지→요소→비율→균일성) | **폰트 사이징 참고** |
| **BabelDOC** | IL 중간언어, optimal_scale 타이프세팅 | **스케일링 알고리즘 참고** |
| **LLM_PDF_Translator** | 이미지 우선 접근 (pdf2image→OCR→번역→ReportLab) | **비채택 (의존성 과다)** |

### 핵심 발견: PyMuPDF `insert_htmlbox()`

```python
spare_height, scale = page.insert_htmlbox(
    rect,           # 대상 영역
    text,           # HTML 문자열
    css=None,       # CSS 스타일링
    scale_low=0,    # 최소 축소 비율 (0=무제한, 1=축소 불가)
)
```

- 대상 언어에 맞는 **폰트 자동 선택** (한글 → 본고딕 계열)
- 텍스트가 bbox를 초과하면 **자동 축소** (내부 반복 레이아웃, 최대 20회)
- `scale_low` 파라미터로 **최소 축소 한도** 제어 가능
- 반환값: `(spare_height, scale)` — 남은 높이, 적용된 축소 비율
- CSS 폰트 크기: **px 단위** 사용 (pt × 1.33 = px)
- **이것 하나로 pdf2zh의 폰트 매핑 + 타이프세팅 역할을 대체**

### 핵심 발견: BabelDOC DocLayout-YOLO (레이아웃 감지)

BabelDOC에 내장된 ONNX 모델을 직접 재사용:
```python
from babeldoc.docvision.doclayout import OnnxModel

model = OnnxModel.from_pretrained()
# ~/.cache/babeldoc/models/doclayout_yolo_docstructbench_imgsz1024.onnx (71.8MB)

results = model.predict(image)[0]  # image: numpy BGR array
for box in results.boxes:
    cls_name = results.names[int(box.cls)]  # title, plain text, figure, table, ...
    x1, y1, x2, y2 = box.xyxy               # 좌표 (DPI 72 = PyMuPDF pt 1:1)
    confidence = box.conf
```

감지 클래스 (10종):
```
0: title, 1: plain text, 2: abandon (헤더/푸터),
3: figure, 4: figure_caption, 5: table, 6: table_caption,
7: table_footnote, 8: isolate_formula, 9: formula_caption
```

**실측 결과** (8_Error.pdf 1페이지, 2컬럼 스캔 논문):
- 15개 영역 감지 (title 3, plain text 11, abandon 1)
- 좌/우 컬럼 자연스럽게 분리 (bbox X 좌표로 구분)
- 푸터(IEEE 저작권)를 `abandon`으로 자동 분류 → 번역 제외 가능
- **DPI 72에서 scale=1.0** → bbox 좌표를 `insert_htmlbox()`에 그대로 전달

**X-gap 휴리스틱 대비 장점**:
- title/figure/table/formula/caption 의미적 구분
- figure/table 영역 자동 감지 → 번역 제외 또는 이미지 캡처
- abandon(헤더/푸터) 자동 제외
- 추가 설치 불필요 (BabelDOC 의존성으로 이미 존재)

---

## 3. 폰트 사이즈 전략

### 3.1 문제: 한글 텍스트 확장

| 지표 | 영문 | 한글 | 비율 |
|------|------|------|------|
| 글자 수 | 100자 | ~88자 | 0.88x |
| 글자당 시각 폭 | ~0.5em (가변폭) | ~1.0em (전각) | 2.0x |
| **실효 시각 폭** | 50em | 88em | **1.76x** |

→ 같은 폰트 크기에서 한글이 영문 대비 **1.5~1.8배 넓음**
→ 원본 bbox에 맞추려면 폰트 축소 또는 줄바꿈 증가 필요

### 3.2 채택 전략: 3단계 폰트 사이징

**1단계 — 스마트 기본값 (자동)**
```python
# 원본 블록의 지배적 폰트 크기 추출
original_pt = get_dominant_font_size(block)  # 예: 10pt

# 한글 확장 보정: 0.75배 (경험적 최적값)
base_pt = original_pt * 0.75

# CSS px 변환
base_px = base_pt * 1.33  # 10pt * 0.75 * 1.33 = 9.975px
```

**2단계 — 자동 축소 (insert_htmlbox 내장)**
```python
spare, scale = page.insert_htmlbox(
    bbox, translated,
    css=f"* {{font-family: sans-serif; font-size: {base_px:.1f}px;}}",
    scale_low=0.5  # 기본값의 50% 이하로는 축소하지 않음
)

if spare == -1:
    # 50%에서도 안 맞으면 → scale_low=0 으로 재시도 (무제한 축소)
    spare, scale = page.insert_htmlbox(bbox, translated,
        css=css, scale_low=0)
```

**3단계 — 사용자 조절 (수동)**
```
번역 툴바:  [...] [모델▼] (●PDF ○텍스트) [A-][A+] [이 페이지 번역] [범위 번역]
                                          ↑ 폰트 크기 ±10%
```
- `[A-]` `[A+]` 버튼으로 폰트 스케일 조절 (0.5x ~ 1.5x, 기본 1.0x)
- 조절 시 PDF 재생성 요청 (변경된 scale로 text-translate API 재호출)
- `localStorage('tt-font-scale')` 에 유지

### 3.3 BabelDOC식 점진적 스케일링 (참고 구현)

BabelDOC 타이프세팅 알고리즘 핵심:
```
scale = 1.0, line_spacing = 1.5

while 안맞으면:
    1. line_spacing 먼저 줄임 (1.5 → 1.4, -0.1 단위)
    2. 그래도 안맞으면 scale 줄임 (>0.6: -0.05, ≤0.6: -0.1)
    3. scale < 0.7 이면 min_line_spacing도 1.1까지 허용
    4. scale < 0.1 이면 포기
```

→ `insert_htmlbox()`가 내부적으로 유사하게 동작하므로,
   우리는 `scale_low`와 CSS `line-height`로 제어하면 충분.

### 3.4 폰트 크기 관련 config 추가

```python
# backend/config.py
TRANSLATOR_TEXT_FONT_SCALE = 0.75      # EN→KR 기본 축소 비율
TRANSLATOR_TEXT_MIN_SCALE = 0.5        # insert_htmlbox scale_low
TRANSLATOR_TEXT_FONT_FAMILY = "sans-serif"
```

Settings GUI에서 조절 가능하도록 노출.

---

## 4. 프론트엔드 UI 설계

### 4.1 현재 툴바 구조
```
[줌-][100%][줌+] [동기화] <spacer> [상태] [모델▼] [이 페이지 번역] [범위 번역] [취소]
```

### 4.2 변경 후 툴바 구조
```
[줌-][100%][줌+] [동기화] <spacer> [상태] [모델▼] (●PDF ○텍스트) [A-][A+] [이 페이지 번역] [범위 번역] [취소]
```

변경 요소:
- **라디오버튼 `(●PDF ○텍스트)`**: 번역 엔진 선택. 모델 셀렉트 뒤, 번역 버튼 앞
- **`[A-][A+]`**: 텍스트 모드에서만 표시. 폰트 스케일 조절 (±10%)
- **번역 버튼 공유**: 기존 `이 페이지 번역`, `범위 번역` 버튼은 그대로. 선택된 엔진으로 요청

### 4.3 동작 흐름

```
사용자가 라디오 "텍스트" 선택
  → [A-][A+] 버튼 표시
  → [이 페이지 번역] 클릭
  → POST /api/translator/.../text-translate (pdf2zh 대신 자체 엔진)
  → 폴링 → 완료 시 text_translated.pdf 로드 (기존 PDF.js 뷰어)

사용자가 라디오 "PDF" 선택 (기본)
  → [A-][A+] 숨김
  → [이 페이지 번역] 클릭
  → 기존 pdf2zh 파이프라인 그대로
```

### 4.4 캐싱 및 상태 전환

- 라디오 전환 시, 해당 모드의 기존 번역 결과가 있으면 즉시 표시
- 없으면 "이 페이지는 아직 번역되지 않았습니다" 표시
- 두 모드의 결과가 독립적으로 캐시됨 (같은 페이지에 pdf2zh + 텍스트 결과 공존 가능)

### 4.5 폰트 크기 조절 UX

```
[A-] 클릭 → font_scale -= 0.1 (최소 0.5)
[A+] 클릭 → font_scale += 0.1 (최대 1.5)
  → 기존 텍스트 번역 결과가 있으면 재생성 요청
  → POST /api/.../text-translate?font_scale=0.8
  → 새 PDF 로드
```

- 현재 scale 표시: `[A-] 90% [A+]` 형태
- localStorage에 저장, 세션 유지

---

## 5. 설계 상세

### 5.1 아키텍처 개요

```
[원본 PDF 페이지]
       |
       v
  1. DocLayout-YOLO 레이아웃 감지 (OnnxModel.predict)
     └── 15개 영역 감지: title, plain text, figure, table, abandon, ...
       |
       v
  2. 영역 분류 및 텍스트 추출
     ├── 번역 대상: title, plain text → PyMuPDF get_text("dict", clip=bbox)
     ├── 이미지 캡처: figure, table → get_pixmap(clip=bbox)
     └── 제외: abandon (헤더/푸터), formula (이미지 캡처)
       |
       v
  3. Ollama 번역
     ├── 좌컬럼 텍스트 → 번역 요청
     ├── 우컬럼 텍스트 → 번역 요청
     └── 전폭 텍스트 → 번역 요청
       |
       v
  4. PDF 재구성 (새 페이지)
     ├── 흰색 배경 (풀페이지)
     ├── figure/table/formula → 원본 이미지 캡처 삽입
     └── title/text → insert_htmlbox() (번역 텍스트, YOLO bbox, font_scale)
       |
       v
  [번역 PDF] → 우측 패널 (PDF.js)
```

### 5.2 레이아웃 감지 및 텍스트 추출

```python
import numpy as np
from babeldoc.docvision.doclayout import OnnxModel

# 1. DocLayout-YOLO 레이아웃 감지
model = OnnxModel.from_pretrained()  # 싱글턴으로 캐시
pix = page.get_pixmap(dpi=72)        # scale=1.0 → bbox 좌표 = pt 좌표
image = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width, 3)[:,:,::-1]
results = model.predict(image)[0]

# 2. 영역 분류
translate_regions = []   # title, plain text → 번역 대상
capture_regions = []     # figure, table, formula → 이미지 캡처
page_center = page.rect.width / 2

for box in results.boxes:
    cls = results.names[int(box.cls)]
    bbox = fitz.Rect(box.xyxy)

    if cls in ('title', 'plain text'):
        text = page.get_text("text", clip=bbox).strip()
        if text:
            column = 'left' if bbox.x0 + bbox.width/2 < page_center else 'right'
            if bbox.width / page.rect.width > 0.6:
                column = 'full'
            translate_regions.append({
                'bbox': bbox, 'text': text, 'cls': cls, 'column': column
            })
    elif cls in ('figure', 'table', 'isolate_formula'):
        capture_regions.append({'bbox': bbox, 'cls': cls})
    # abandon(헤더/푸터), caption → 제외 또는 별도 처리
```

### 5.3 번역 전략

**페이지 단위 번역 (컨텍스트 유지)**:
- 전폭 블록 → 하나의 번역 요청
- 좌측 컬럼 전체 → 하나의 번역 요청
- 우측 컬럼 전체 → 하나의 번역 요청
- 블록 경계를 `\n---\n` 구분자로 구분, 번역 후 다시 분리

**Ollama 직접 호출** (pdf2zh 미사용):
```python
response = ollama.chat(model=model, messages=[
    {"role": "system", "content": "Translate English to Korean. Keep --- separators."},
    {"role": "user", "content": text_with_separators}
])
```

### 5.4 PDF 재구성 (폰트 사이징 적용)

```python
import fitz

def build_text_translated_pdf(orig_page, translations, blocks,
                               font_scale=0.75, min_scale=0.5,
                               include_images=True, include_tables=False):
    new_doc = fitz.open()
    new_page = new_doc.new_page(
        width=orig_page.rect.width,
        height=orig_page.rect.height
    )

    # 1. 이미지 삽입 (옵션, 풀페이지 스캔 이미지는 제외)
    if include_images:
        for img_info in orig_page.get_images(full=True):
            xref = img_info[0]
            for rect in orig_page.get_image_rects(xref):
                # 풀페이지 이미지 제외 (스캔 PDF 보호)
                coverage = (rect.width * rect.height) / \
                           (orig_page.rect.width * orig_page.rect.height)
                if coverage > 0.9:
                    continue  # 스캔 이미지 스킵
                img_data = orig_doc.extract_image(xref)
                new_page.insert_image(rect, stream=img_data["image"])

    # 2. 표 삽입 (옵션, 이미지 캡처)
    if include_tables:
        for table in orig_page.find_tables():
            clip = fitz.Rect(table.bbox)
            pix = orig_page.get_pixmap(clip=clip, dpi=150)
            new_page.insert_image(clip, pixmap=pix)

    # 3. 번역 텍스트 삽입 (폰트 사이징)
    for block, translated in zip(blocks, translations):
        bbox = fitz.Rect(block["bbox"])
        orig_pt = get_dominant_font_size(block)
        target_px = orig_pt * 1.33 * font_scale

        css = f"* {{font-family: sans-serif; font-size: {target_px:.1f}px; color: black;}}"

        spare, scale = new_page.insert_htmlbox(
            bbox, translated, css=css, scale_low=min_scale
        )

        # 최소 스케일에서도 안 맞으면 무제한 축소
        if spare == -1:
            new_page.insert_htmlbox(bbox, translated, css=css, scale_low=0)

    new_doc.subset_fonts()
    return new_doc
```

### 5.5 백엔드 API

```
POST /api/translator/document/{doc_id}/page/{page_num}/text-translate
Body: {
    "model": "translategemma:4b",
    "font_scale": 0.75,
    "include_images": true,
    "include_tables": false
}
Response: { "status": "done" }

GET /api/translator/document/{doc_id}/page/{page_num}/text-translated.pdf
Response: 번역된 PDF 파일

GET /api/translator/document/{doc_id}/page/{page_num}/text-status
Response: { "status": "done|translating|error", ... }
```

### 5.6 저장 구조

```
data/translator/{username}/{doc_id}/pages/{N}/
  ├── translated.pdf          ← pdf2zh 결과 (기존)
  ├── text_translated.pdf     ← 자체 렌더링 결과 (신규)
  └── text_mapping.json       ← 블록 매핑 (향후 마킹 동기화용)
```

> **향후 확장 참고**: `text_mapping.json`은 마킹(형광펜) 동기화 기능의 기반 데이터.
> 각 블록의 `source_rect`, `target_rect`, `source_text`, `target_text`를 기록.
> 상세: `workbench/plans/marking-sync-feasibility.md` 참조.

### 5.7 meta.json 확장

```json
{
  "page_status": {
    "1": {
      "status": "done",
      "model": "translategemma:4b",
      "text_translate": {
        "status": "done",
        "model": "translategemma:4b",
        "font_scale": 0.75,
        "include_images": true,
        "translated_at": "2026-03-06T..."
      }
    }
  }
}
```

---

## 6. 구현 순서

### Phase 1: 핵심 엔진 (백엔드)
1. `services/text_translator.py` 신규
   - 텍스트 추출 (`get_text("dict")`)
   - 컬럼 감지 (X-gap 분석)
   - Ollama 번역 (직접 호출)
   - PDF 재구성 (`insert_htmlbox()` + 폰트 사이징)
   - 이미지/표 삽입 (옵션)
2. `api/translator.py` 확장 — text-translate / text-status / text-pdf 엔드포인트
3. `config.py` — TRANSLATOR_TEXT_* 설정 추가
4. meta.json 스키마 확장

### Phase 2: 프론트엔드 통합
5. 툴바 라디오버튼 (PDF/텍스트) + [A-][A+] 폰트 조절
6. 번역 버튼 클릭 시 선택된 모드에 따라 API 분기
7. 텍스트 번역 폴링/표시 로직 (기존 PDF 폴링과 동일 패턴)
8. 모드 전환 시 캐시된 결과 즉시 표시

### Phase 3: 품질 개선
9. 번역 프롬프트 튜닝 (학술논문 특화)
10. Settings GUI에 텍스트 번역 옵션 노출
11. 스캔 PDF 자동 감지 → 텍스트 모드 권장 알림

---

## 7. 기술적 판단

### 채택하는 것
- **BabelDOC DocLayout-YOLO (ONNX)**: 이미 설치/캐시됨 (71.8MB), 10클래스 레이아웃 감지, DPI 72에서 PyMuPDF 좌표와 1:1 매핑
- **PyMuPDF `insert_htmlbox()`**: 폰트 자동선택 + `scale_low` 제어 → 별도 폰트 관리 불필요
- **PDF 출력**: 기존 PDF.js 뷰어 재사용, UI 변경 최소화
- **Ollama 직접 호출**: pdf2zh 우회, 기존 인프라 활용
- **figure/table/formula → 이미지 캡처 삽입**: YOLO가 영역 감지, 원본 캡처가 안정적
- **3단계 폰트 사이징**: 스마트 기본값 → 자동 축소 → 사용자 조절
- **abandon 자동 제외**: 헤더/푸터를 YOLO가 자동 분류 → 번역 불필요 영역 제거

### 채택하지 않는 것
- **X-gap 휴리스틱 컬럼 감지**: DocLayout-YOLO가 더 정확. YOLO 실패 시 폴백으로만 참고
- **HTML 출력**: PDF.js 뷰어 재활용 불가, UI 변경 범위 큼
- **pdfminer.six 직접 사용**: PyMuPDF `get_text("dict")`로 충분
- **LaTeX/DOCX 중간 형식**: 과도한 복잡도, 왕복 손실

### 리스크 및 완화
| 리스크 | 완화 |
|--------|------|
| `insert_htmlbox()` 자동 축소가 과해 텍스트가 너무 작아짐 | `scale_low=0.5` 기본 제한 + 사용자 A-/A+ 조절 |
| YOLO 감지 실패 (낮은 conf, 누락 영역) | conf>0.25 필터링 + X-gap 휴리스틱 폴백 |
| pdf2zh의 용어 추출/포뮬러 보존 기능 없음 | figure/table/formula를 YOLO가 감지 → 이미지 캡처로 원본 보존 |
| Ollama 번역 시 블록 구분자(`---`) 유실 | 번역 후 블록 수 불일치 시 단일 블록 폴백 |
| BabelDOC 버전 업데이트 시 내부 API 변경 | OnnxModel import를 try/except로 감싸고, 실패 시 X-gap 폴백 |

---

## 8. 예상 효과

| 시나리오 | pdf2zh 모드 | 텍스트 번역 모드 |
|---------|------------|---------------|
| 네이티브 텍스트 PDF | **최적** (레이아웃 보존) | 양호 (좌표 기반 배치) |
| 스캔 PDF | 겹침 발생 | **최적** (흰 배경 재구성) |
| 복잡한 레이아웃 | 가끔 깨짐 | 단순화되지만 읽기 가능 |
| 수식 포함 PDF | 수식 보존 | 수식 미보존 (이미지로 대체 가능) |
| 암호화/손상 PDF | 실패 가능 | 텍스트 추출만 되면 동작 |
| 폰트 크기 불만족 | 조절 불가 | **[A-][A+]로 즉시 조절** |

두 모드가 상호 보완하여 **거의 모든 PDF 유형**을 커버합니다.
