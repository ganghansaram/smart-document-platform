# Plan-39 — DOCX 캡션 하이픈 손실 문제 진단

**상태**: 진단 단계 (원인 후보 좁힘 완료, 확정 미완)
**작성**: 2026-04-23
**관련 시스템**: `tools/converter/`, `tools/docx2html-standalone/`, `tools/heading-numberer/`
**관련 메모리**: `memory/MEMORY.md` — "STYLEREF + SEQ 합성 캡션", "장절번호 평문화"

---

## 1. 증상

- Word 원문에 `그림 4-6. 중량비 비교` 같은 캡션이 있음
- 사용자가 **매크로로 평문화** 후 저장 → 육안 검사 시 `그림 4-6`으로 정상 보임
- 이 docx를 우리 변환기로 HTML 변환 시 → `그림 46. 중량비 비교` (하이픈 **탈락**)
- 다른 위치의 `4-1`, `4-2` 등 동일 패턴도 같은 증상 추정

## 2. Word 캡션의 내부 구조 (배경)

"그림 4-6"은 대부분 필드 합성으로 저장됨:

```xml
<w:p>
  <w:r><w:t>그림 </w:t></w:r>

  <!-- ① STYLEREF "제목 1" → cache "4" -->
  <w:r><w:fldChar w:fldCharType="begin"/></w:r>
  <w:r><w:instrText> STYLEREF "제목 1" \s </w:instrText></w:r>
  <w:r><w:fldChar w:fldCharType="separate"/></w:r>
  <w:r><w:t>4</w:t></w:r>
  <w:r><w:fldChar w:fldCharType="end"/></w:r>

  <w:r><w:t>-</w:t></w:r>   ← 하이픈 literal run

  <!-- ② SEQ Figure \s 1 → cache "6" -->
  <w:r><w:fldChar w:fldCharType="begin"/></w:r>
  <w:r><w:instrText> SEQ Figure \* ARABIC \s 1 </w:instrText></w:r>
  <w:r><w:fldChar w:fldCharType="separate"/></w:r>
  <w:r><w:t>6</w:t></w:r>
  <w:r><w:fldChar w:fldCharType="end"/></w:r>

  <w:r><w:t>. 중량비 비교</w:t></w:r>
</w:p>
```

4와 6은 각각 **필드 결과(cache)**, 하이픈은 **두 필드 사이의 독립 run**.

## 3. 재현 테스트 (완료)

### 3.1 입력 준비
`/tmp/caption-test/flattened_sample.docx` (python-docx 생성, 순수 literal text):
```xml
<w:p><w:r><w:t>그림 4-1. 중량비 비교</w:t></w:r></w:p>
<w:p><w:r><w:t>그림 4-2. 추력 비교</w:t></w:r></w:p>
<w:p><w:r><w:t>표 4-3. 실험 데이터</w:t></w:r></w:p>
<w:p><w:pPr><w:pStyle w:val="Caption"/></w:pPr><w:r><w:t>그림 4-4. 속도 그래프</w:t></w:r></w:p>
```

### 3.2 변환기 실행 결과
```html
<p id="fig-4-1" class="caption">그림 4-1. 중량비 비교</p>
<p id="fig-4-2" class="caption">그림 4-2. 추력 비교</p>
<p id="tbl-4-3" class="caption">표 4-3. 실험 데이터</p>
<p id="fig-4-4" class="caption">그림 4-4. 속도 그래프</p>
```

**결론**: 필드 없는 순수 literal text 입력 시 변환기는 하이픈을 완벽히 보존.

### 3.3 standalone 검토
- `tools/docx2html-standalone/docx2html.py` (206줄) = 단순 CLI/GUI 래퍼
- PyInstaller `spec` 의 `pathex=[_ENGINE_DIR]` 이 `../converter/` 참조
- **엔진은 `tools/converter/converter.py` 하나** — standalone도 동일 코드

### 3.4 하이픈 제거 코드 grep
`tools/converter/` 전체 grep 결과:
- 하이픈 삭제·치환 로직 **없음**
- `converter.py:1725` `number.replace('.', '-')` — 캡션 ID 생성 시 점→하이픈 **역방향**
- 나머지는 전부 `strip()` (공백 trim)

## 4. 원인 분석

### 가설 1 (최유력) — 평문화 매크로의 **부분 평문화**
- 사용자 매크로가 heading numbering(numPr)만 평문화하고 **STYLEREF/SEQ 필드는 그대로 살아있음**
- Word 뷰어에서는 필드 cache가 "4-6"으로 보이지만 XML 내부엔 필드 구조 잔존
- 우리 변환기 `_resolve_seq_fields` (converter.py:1555) 는 `\s N` 스위치(heading reset)를 만나면
  **cache 무시하고 카운터로 재계산** (converter.py:1620~1628)
- 결과: `4`(STYLEREF cache 유지) + `-`(literal run 유지) + `6`(SEQ 재계산값) → 형식상 정상 출력되어야 함
- 그러나 cache 값이 다른 원인(예: cache가 "4-6" 전체를 한 run으로 묶고 있는 비정상 구조)으로 저장됐다면
  변환 과정에서 하이픈만 소실되는 시나리오 가능

### 가설 2 — Word AutoCorrect 치환
- 매크로가 `Fields.Unlink()` 로 필드 언링크 시, Word AutoCorrect가 ASCII 하이픈(`-`, U+002D)을
  **en-dash(`–`, U+2013)** · **non-breaking hyphen(`‑`, U+2011)** · **soft hyphen(`­`, U+00AD)** 등으로 치환
- Soft hyphen은 렌더링 시 잘 안 보이지만 HTML 추출 시점에 잔존 가능
- 변환 과정 중 특정 유니코드 normalize·strip 에서 제거되면 시각적으로 "46"처럼 보임

### 가설 3 (기각) — 우리 변환기 버그
- 재현 테스트(3.2)와 코드 검토(3.4)로 **확실히 기각**

## 5. 확정을 위해 필요한 것

사용자 실제 원문은 공유 제약 있음. 다음 중 하나가 있어야 단정 가능:

### 옵션 A — 사용자 자가 진단 (최소 비용)
1. 문제 docx를 Word에서 열기
2. `Ctrl+A` (전체 선택) → `Alt+F9` (필드 코드 토글)
3. `{ STYLEREF ... }` 중괄호가 보이면 → **가설 1 확정**
4. 필드 없는데 하이픈만 이상하면 → `Ctrl+F`로 "-" 검색·복사 → 메모장 붙여넣기 → 바이트 크기로 유니코드 판별 → 3바이트면 **가설 2 확정**

### 옵션 B — 공유 가능한 더미 docx
- 같은 매크로를 **민감 정보 없는 샘플** 에 돌려 결과 공유
- 수신 후 즉시 `zipfile` → `word/document.xml` 뜯어 `<w:p>` 블록 분석 → 확정

## 6. 후속 조치 옵션

### 가설 1 확정 시
- **매크로 개선**: `Ctrl+A` → `Ctrl+Shift+F9` 등가 동작(`Selection.Fields.Unlink` 전역) 추가
- **또는 변환기 보강**: `_resolve_seq_fields` 의 cache 재계산 경로에서 cache가 "정상"으로 보이면 존중하도록 조건 강화 (단, 이중 소스로 인한 sync 문제 남음)
- 권장: **매크로 개선 쪽** (가설 2 완전 커버 가능한 `Fields.Unlink` + AutoCorrect 비활성화)

### 가설 2 확정 시
- 매크로에서 `Application.AutoCorrect.ReplaceText = False` 일시 OFF 후 언링크
- 또는 언링크 직후 `Selection.Find.Execute` 로 en-dash/NBHY → ASCII hyphen 역치환

### 양쪽 다 놓쳤을 경우 보험
- 변환기 진입부에서 `document.xml` 읽을 때 각 `<w:t>` 텍스트 대상
  `\u2013`/`\u2011`/`\u00AD` → `-` 정규화 pass 추가 (저위험, 원본 훼손 없음)

## 7. 참고 코드 위치

- `tools/converter/converter.py:1411` — `_resolve_styleref_fields`
- `tools/converter/converter.py:1555` — `_resolve_seq_fields` (복합/단순 필드 모두 처리)
- `tools/converter/converter.py:1620~1628` — **cache 무시 + 재계산 조건** (가설 1 핵심)
- `tools/converter/converter.py:1667` — `_detect_caption` (캡션 패턴 인식)
- `tools/converter/numbering_resolver.py` — STYLEREF·SEQ 번호 생성 폴백
- `tools/heading-numberer/heading_numberer.py` — 우리가 제공한 평문화 도구 (heading numPr 전용, 필드 미대상)
- `tools/docx2html-standalone/docx2html.py` — standalone 래퍼 (엔진은 `tools/converter/` 공유)

## 8. 재개 시 첫 스텝

1. 사용자에게 가설 1 자가 진단 결과(Alt+F9) 확인
2. 옵션 B 샘플 받을 수 있는지 재확인
3. 확정 후 위 "6. 후속 조치 옵션" 중 선택 구현
