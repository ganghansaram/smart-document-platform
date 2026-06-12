# 번역기 스캔 PDF 겹침 문제 — 테스트 계획

## 1. 문제 진단

### 증상
- `8_Error.pdf` 1페이지 번역 결과: **영문 원문 위에 한글 번역이 겹쳐서 출력**
- 원본이 2중 컬럼 논문인데 텍스트 드래그 시 단일 컬럼처럼 선택됨

### 원인 분석
원본 PDF는 **스캔본 (이미지 기반 PDF)**:
- 2550×3300 풀페이지 이미지가 페이지 전체(100%)를 덮고 있음
- 그 위에 OCR 텍스트 레이어 (Courier 폰트, 불규칙 사이즈) 존재
- pdf2zh(BabelDOC)는 OCR 텍스트 레이어만 번역/교체하지만,
  **밑에 깔린 이미지의 영문 텍스트는 그대로** → 겹침 발생

### 구조
```
┌─────────────────────────┐
│  [3] 번역된 한글 텍스트    │  ← pdf2zh가 교체한 레이어
│  [2] (제거됨) OCR 텍스트   │  ← 원래 있던 투명 OCR 레이어
│  [1] 풀페이지 스캔 이미지   │  ← 영문 원문이 보이는 이미지 (그대로)
└─────────────────────────┘
```

---

## 2. 사용 가능한 pdf2zh-next / BabelDOC 옵션

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--ocr-workaround` | 스캔 PDF 핵심 옵션. 각 문단 영역에 **흰색 사각형**을 깔아 원본 이미지 텍스트를 덮은 뒤 번역 텍스트 배치. `--skip-scanned-detection`과 `--disable-rich-text-translate` 자동 활성화 | `False` |
| `--auto-enable-ocr-workaround` | 자동 스캔 감지 (SSIM > 0.95 per page, >80% pages → 스캔 판정) 후 `--ocr-workaround` 동적 활성화 | `False` |
| `--enhance-compatibility` | `--skip-clean` + `--dual-translate-first` + `--disable-rich-text-translate` 일괄 활성화. PDF 뷰어 호환성 개선 | `False` |
| `--disable-rich-text-translate` | 리치 텍스트 서식 보존 비활성화. 단순화된 텍스트 출력 | `False` |
| `--skip-clean` | PDF 정리/최적화 단계 스킵. 파일 커지지만 호환성 향상 | `False` |
| `--skip-scanned-detection` | 스캔 문서 감지 단계 건너뜀 | `False` |
| `--split-short-lines` | 짧은 줄 분할 (컬럼 레이아웃에 도움 가능) | `False` |
| `--translate-table-text` | 표 내부 텍스트도 번역 | `False` |
| `--custom-system-prompt` | 번역 모델에 커스텀 프롬프트 전달 | `""` |
| `--primary-font-family` | 번역 출력 폰트. 현재 `sans-serif` | `sans-serif` |

### 핵심 메커니즘: `--ocr-workaround`
1. 각 감지된 문단 영역에 **흰색 배경 사각형** (`PdfRectangle`, fill_background=True) 그림
2. 모든 문자 색상을 **검정(BLACK)** 으로 강제
3. 원본 PDF 문자 제거 (`page.pdf_character = []`)
4. 가비지 컬렉션 레벨 4 (공격적 정리)

**제한사항**:
- 흰 배경 + 검정 텍스트 문서에서만 효과적
- 색상 배경/비검정 텍스트에서는 부자연스러움
- 일부 PDF에서 여전히 겹침 발생 (GitHub Issue #123, 미해결)

### 관련 GitHub 이슈
- BabelDOC #264: "중영문 겹침" → 메인테이너: `--ocr-workaround` 사용 권장
- BabelDOC #446: 레이어 지원 문제, 커뮤니티 후처리 스크립트 존재
- BabelDOC #471: 메인테이너 입장 — "스캔 파일은 BabelDOC의 의도된 사용 사례가 아님"
- PDFMathTranslate-next #123: `--ocr-workaround`로도 겹침 해결 안 되는 케이스 (미해결)
- PDFMathTranslate-next #285: PaddleOCR VL 통합 → 상용 버전으로 클로즈드소스 예정

---

## 3. 테스트 계획

### 테스트 문서
- `8_Error.pdf` — 6페이지, 2중 컬럼, 풀페이지 스캔 이미지 + OCR 레이어
- 테스트 대상: **1페이지** (빠른 반복 테스트)

### 테스트 환경
- 모델: `translategemma:4b` (현재 사용 중, 1페이지 ~85초)
- 기존 커맨드 기본 옵션: `--pages 1 --only-include-translated-page --no-dual --primary-font-family sans-serif`

### 테스트 시나리오

#### Test 1: `--ocr-workaround` 단독
**목적**: 가장 직접적인 해결책 검증
**추가 옵션**: `--ocr-workaround`
**기대**: 흰색 사각형이 원본 이미지 텍스트를 덮고, 번역 텍스트만 표시
**확인**: 겹침 해소 여부, 흰색 사각형 경계 자연스러움, 2컬럼 레이아웃 유지 여부

#### Test 2: `--auto-enable-ocr-workaround` 단독
**목적**: 자동 감지 → 자동 적용 동작 확인
**추가 옵션**: `--auto-enable-ocr-workaround`
**기대**: 스캔 감지 후 Test 1과 동일한 결과
**확인**: 스캔 감지 정상 동작 여부, 결과 품질 Test 1과 동일한지

#### Test 3: `--ocr-workaround` + `--enhance-compatibility`
**목적**: 호환성 옵션 병행 시 품질 개선 여부
**추가 옵션**: `--ocr-workaround --enhance-compatibility`
**기대**: 더 깨끗한 출력 (skip-clean으로 원본 구조 보존)
**확인**: PDF 뷰어 렌더링 품질, 파일 크기 변화

#### Test 4: `--ocr-workaround` + `--split-short-lines`
**목적**: 2중 컬럼 레이아웃에서 줄 분할 개선
**추가 옵션**: `--ocr-workaround --split-short-lines`
**기대**: 컬럼 경계에서의 텍스트 흐름 개선
**확인**: 번역 텍스트가 컬럼 경계를 넘지 않는지

#### Test 5: `--ocr-workaround` + `--translate-table-text`
**목적**: 표 내부 텍스트 번역 포함
**추가 옵션**: `--ocr-workaround --translate-table-text`
**기대**: 표 내부 영문도 번역됨
**확인**: 표 레이아웃 유지 여부, 표 내부 겹침 여부

#### Test 6: 최적 조합 (Test 1~5 결과 기반)
**목적**: 가장 좋은 결과를 낸 옵션 조합 최종 확인
**추가 옵션**: Test 1~5 결과를 바탕으로 결정
**확인**: 전체 6페이지 번역 품질, 일관성

### 각 테스트 평가 기준

| 항목 | 평가 방법 |
|------|-----------|
| 겹침 해소 | 번역 PDF에서 영문 원문이 보이지 않는지 육안 확인 |
| 레이아웃 | 2컬럼 구조 유지, 텍스트 넘침 없음 |
| 가독성 | 번역 텍스트 폰트 크기/간격 적절한지 |
| 흰색 마스크 | 마스크 경계가 자연스러운지, 여백 적절한지 |
| 번역 품질 | 한글 번역 내용의 정확성 (모델 의존) |
| 처리 시간 | 옵션 추가로 인한 시간 증가 |
| 파일 크기 | 결과 PDF 크기 |

---

## 4. 테스트 실행 방법

### CLI 직접 실행 (빠른 반복)
```bash
# Test 1
pdf2zh --ollama --ollama-model translategemma:4b \
  --ollama-host http://localhost:11434 \
  --lang-in English --lang-out Korean \
  --primary-font-family sans-serif \
  --pages 1 --only-include-translated-page --no-dual \
  --ocr-workaround \
  --output /tmp/test1 \
  "data/translator/admin/20260305_234642_837560/original.pdf"
```

### 웹 UI 통한 테스트
1. 기존 번역 결과 삭제 (meta.json의 page_status 리셋)
2. `config.py`에서 해당 옵션 활성화
3. 웹에서 1페이지 번역 재실행
4. 결과 PDF 확인

### 설정 변경 방법 (Settings GUI)
현재 `TRANSLATOR_OCR_WORKAROUND`, `TRANSLATOR_ENHANCE_COMPAT`가
`config.py`에 정의되어 있고 `translator_service.py`에서 CLI 옵션으로 매핑됨.
Settings GUI에서 토글하거나, 직접 `config.py` 수정 후 서버 재시작.

---

## 5. 추가 고려사항

### config.py에 추가할 옵션
```python
TRANSLATOR_AUTO_OCR_WORKAROUND = False  # --auto-enable-ocr-workaround
TRANSLATOR_SPLIT_SHORT_LINES = False    # --split-short-lines
```

### 장기적 대안 (Built-in 해결 안 될 경우)
1. **전처리 접근**: 이미지에서 텍스트 영역 inpainting 후 번역
2. **커뮤니티 후처리 스크립트**: `babeldoc_ocr_mono_fix` (역방향 머지)
3. **네이티브 텍스트 PDF 변환**: OCRmyPDF `--force-ocr` → pdf2zh

### 참고
- BabelDOC 메인테이너: "스캔 파일은 의도된 사용 사례가 아님"
- `--ocr-workaround`는 "experimental" 표기
- 흰배경+검정텍스트 문서에서 가장 효과적
