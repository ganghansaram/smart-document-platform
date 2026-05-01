# Plan-56 — 헤딩 markdown 인식 + 자동 제외 정규식 prefix 정합 검증

> 작성일: 2026-05-01
> 변경 범위: `backend/services/similarity_engine.py` (정규식 3종 + `_build_tagged_html`) + `tests/sim_table_structural_test.py` (8 케이스)
> 검증: 37/37 단위 테스트 PASS + Playwright UI E2E

---

## 1. 배경

### 사용자 페인 (2026-05-01)
> "장절 부분이 풀려서 ## 이런 기호들이 보이는데... 처음 로드했을때와 분석이후 마킹이 적용된 후 문서의 모습이 달라지는 이유가 뭘까?"

### 결함 메커니즘
- `simMdToHtml` (frontend): markdown → `<h{1..6}>` 정상 변환
- `_build_tagged_html` (backend): paragraph 평탄화 → `<p>## 1.1 SCOPE</p>` 노출
- 자동 제외 정규식 3종 모두 `^\s*` 시작 → markdown prefix (`## `) 와 충돌

### 부수 발견 (★ 핵심)
- `_REFERENCES_HEADER_RE` 가 `## References` 미매칭 → **참고문헌 섹션 자동 제외 실패** → 점수 inflated
- `_TOC_HEADING_RE`, `_CAPTION_RE` 도 동일 결함

---

## 2. 변경 항목

### 2-1. 자동 제외 정규식 3종 prefix 옵션 (similarity_engine.py:447~)
```python
_TOC_HEADING_RE = re.compile(r'^\s*(?:#{1,6}\s+)?\d+(\.\d+)*\s+[A-Z가-힣]')
_REFERENCES_HEADER_RE = re.compile(
    r'^\s*(?:#{1,6}\s+)?(References|Bibliography|참고\s*문헌|인용\s*문헌)\b',
    re.IGNORECASE
)
_CAPTION_RE = re.compile(
    r'^\s*(?:#{1,6}\s+)?(Figure|Fig\.?|Table|Tbl\.?|그림|표)\s+\d+',
    re.IGNORECASE
)
```
- `(?:...)?` non-capturing optional → 기존 매칭 100% 보존
- 추가 매칭: `## References`, `## 1.1 SCOPE`, `## Figure 1` 등

### 2-2. `_build_tagged_html` 헤딩 분기 (CommonMark)
```python
_HEADING_RE = re.compile(r'^(#{1,6})\s+(.+)$')

# _build_tagged_html 안에서 표 분기 직전:
h_match = _HEADING_RE.match(sent.strip())
if h_match:
    level = len(h_match.group(1))
    text = h_match.group(2).strip()
    parts.append(f'<h{level} data-sent-idx="{i}" class="sim-sent">{html_mod.escape(text)}</h{level}>')
    i += 1
    continue
```

### 2-3. 단위 테스트 8 케이스 추가
| Case | 검증 |
|------|------|
| L | references_section markdown prefix |
| M | references_section 기존 패턴 회귀 방지 |
| N | toc_heading markdown prefix |
| O | toc_heading 기존 패턴 회귀 방지 |
| P | caption markdown prefix |
| Q | caption 기존 패턴 회귀 방지 |
| R | _build_tagged_html 헤딩 출력 |
| S | h1/h2/h3 다단계 |

---

## 3. 검증 결과

### 3-1. 자동 회귀 — 37/37 PASS
| 검사 | 결과 |
|------|------|
| `sim_table_structural_test.py` | ✅ **19/19** (기존 11 + 신규 8) |
| `sim_block_order_test.py` | ✅ 5/5 |
| `sim_score_v3_unit_test.py` | ✅ 5/5 |
| `sim_merge_adjacent_unit_test.py` | ✅ 8/8 |
| `sim_label_consistency.sh` | ✅ PASS |

### 3-2. Playwright UI E2E

#### Mock DOCX (Heading 1 + 본문 + Heading 2 + 본문 + 표 + Heading 2 참고문헌 + 항목)
**검증 결과**:
- H1 `1.` — `<h1 sim-hl-excluded>` (toc_heading 자동 제외)
- 본문 단락 — `<p sim-hl-paraphrase>` (의역 매칭)
- H2 `1.1 검증 범위` — `<h2 sim-hl-excluded>` (toc_heading 자동 제외)
- 표 헤더 — `<tr sim-hl-excluded>` (table_structural)
- H2 `참고문헌` — `<h2>` (매칭 자체 없음 — references_section 진입으로 매칭 제외)
- ASTM/ISO 항목 — `<p>` (매칭 없음 — references_section 자동 제외)
- ★ **`##` 기호 raw 노출 0건**

#### 점수
- 적용 후: 40% (의역 2 sentence / 정확한 분모)
- 적용 전 가상치: 60%+ (참고문헌 매칭이 분자에 포함되어 inflated 가능성)

### 3-3. 시각 캡처
- `plan56-after-heading-rendered.png` — 헤딩 시각 위계 + 자동 제외 + 표 정상

---

## 4. 영향 분석

### 격리
- 매칭 알고리즘 (split/L1/L3/merge) 무수정
- 표 처리 (Plan-52) 무수정 — 헤딩 분기는 표보다 우선 검사
- 자동 제외 정규식 prefix 옵션 — 기존 매칭 100% 보존
- 다른 변환기 (translator/explorer) 무영향
- 프론트 무수정

### 점수 정확도 향상
- 참고문헌 섹션 자동 제외 정상화 → 학술/공식 문서 inflation 해소
- 헤딩 (toc_heading) + 캡션 (caption) 자동 제외 정상화

### Plan-54 (자동 제외 시각 신호) 와의 통합
- 헤딩 자동 제외 매칭에 `sim-hl-excluded` 클래스 부여 (Plan-54 simApplyHighlights)
- ⚠️ 단, CSS `.sim-md-view p.sim-hl.sim-hl-excluded` 셀렉터에 `<h{1..6}>` 미포함 → 자동 제외 헤딩의 시각 신호 (회색/점선) 약함
- **후속 hotfix 권장** — CSS 셀렉터에 `h1~h6` 추가

### 잔여 위험
- 점수 변동: 참고문헌 inflated 케이스에서 점수 감소 (긍정 방향, 정확도 향상)
- 사용자 인지 변화: 이전 보고서 대비 점수 다를 수 있음 (운영 측 안내 필요)

---

## 5. UX/UI 전문가 관점

### 시각 위계 회복
- 검사 후에도 H1 (큰 글씨) / H2 (중간) / H3 (작음) / 본문 P 시각 위계 보존
- 첫 업로드 vs 검사 후 시각 일관성 회복

### 자동 제외 매칭 분포 변화
- 헤딩 자동 제외 매칭 증가 → 본문에 회색 영역 늘어남 (Plan-54 시각 신호)
- "이 매칭은 점수 안 들어간다" 사용자 인지 명확

---

## 6. 한 줄 결론

**PASS.** Plan-56 완료 — 헤딩 markdown 인식 (CommonMark `<h{1..6}>` 변환) + 자동 제외 정규식 3종 prefix 정합. 사용자 페인 (`##` 기호 노출) 직접 해소 + 참고문헌 자동 제외 정상화로 점수 정확도 회복. 단위 테스트 37/37 PASS, 매칭 알고리즘 무수정. 후속 — `<h{1..6}>` 자동 제외 시각 신호 CSS hotfix 권장.
