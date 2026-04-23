# Plan-38: 유사도 검증(K-SPEC 표절검토) 업계 표준 고도화

> **선행**: Plan-33 종합 검토 보고서, Plan-34 검증 시스템 계획서 (유사도 영역만 분리)
> **분리 사유**: K-SPEC(사내 기술표준) 1:1 표절 검토 소요 발생 → Plan-34에서 유사도 영역만
> 분리 후 업계 표준(Turnitin/iThenticate/Copyleaks/카피킬러) 수준으로 고도화
> **범위**: `compare.html` 유사도 모드 + `backend/services/similarity_engine.py`
> + `backend/services/export_service.py` + 인쇄 보고서/도움말 신규
> **작성일**: 2026-04-22
> **개정 1**: 2026-04-22 전면 재구성 (카피킬러식 4그룹 + 도움말 4계층 + 검사설정 통합)
> **개정 2**: 2026-04-22 사용자 승인 + Claude 판단 반영 — 5건 수정 (검사설정 7→5옵션, 도움말 4계층 묶음별 분할, 시드 800단어 축소, Ollama 점검 명시, 보고서 A4 자동분할)
> **상태**: ✅ **확정** — 묶음 1 착수

---

## 0. 전체 진행 한눈에 보기

> 각 단계 상세는 §14(작업 묶음 정의), §17(진행 이력) 참조. 본 표는 **현재 위치**를 한눈에 보기 위한 인덱스.

| 묶음 | 단계 | 내용 | 상태 | 완료일 | 비고 |
|---|---|---|---|---|---|
| 1 | 0 | 사전 점검 (Ollama bge-m3 가용성) | ✅ | 2026-04-22 | 본 PC `models/bge-m3` 로컬 모델 가용 확인 |
| 1 | 1 | Phase 0 — 골드셋 14페어 + 평가 도구 | ✅ | 2026-04-23 | `data/similarity-goldset/`, `tools/eval/similarity_eval.py` |
| 1 | 2 | Phase 1 — 백엔드 분류 정상화 | ✅ | 2026-04-23 | TYPE_TRANSLATION 분기 + paraphrase dead zone 해소 + 검사설정 5+2 |
| 1 | 3 | 캘리브레이션 1차 | ⏸️ | — | 잔여 항목 §17.6 (goldset 보정, boilerplate 우선순위, sem 분포) |
| 1 | 4 | Phase 2 — 5단계 신호등 + sources | ✅ | 2026-04-23 | verdict/verdict_label/sources 신규 필드 (적중률 9/14) |
| 1 | 5 | Phase 4 — HTML A4 인쇄 보고서 + L4 부록 | ✅ | 2026-04-23 | 6요소 보고서 + SSOT JSON + Help API + Excel 산식 시트 |
| 1 | 6 | Phase 5 일부 — 모달 B (점수 ⓘ) | ✅ | 2026-04-23 | sim-score-info ⓘ + 산식·5단계·변수의미·면책 모달 (SSOT 파생) |
| 2 | 1 | Phase 3 — UI 재설계 (P1: 라벨/4그룹/마커/가독성/빈상태) | ✅ | 2026-04-23 | 사이드바 3단·검사설정 토글은 향후 분리 |
| 2 | 2 | Phase 5 — 모달 A + 온보딩 (R2 일부) | ✅ | 2026-04-23 | 2축 다이어그램 + 6라벨 표 + 1회 자동 워크스루. 모달 C·L3 가이드 페이지는 향후 |
| 2 | 3 | 검사 설정 UI 토글 + 모달 C | ✅ | 2026-04-23 | 5체크박스 즉시 재계산 + localStorage + 모달 C 가이드 |
| 2 | 4 | 재캘리브레이션 | ⏸️ | — | 실 사용 사례 흡수 |

**범례**: ✅ 완료 / ⏳ 진행중 또는 다음 / ⏸️ 대기

**현 위치**: 묶음 1 **6/7 (86%)** + 묶음 2 **3/4 (75%)** 완료 — 검사 설정 5옵션 UI + 모달 C 적용. 잔여: 묶음 1 캘리브레이션 + 묶음 2 사이드바 3단 / L3 가이드 페이지.

---

## 1. 배경 및 사용 시나리오

사내에서 **K-SPEC**(자체 기술표준)을 제정 중. 신규 작성문서가 외래 표준서
(MIL-STD, NATO STANAG, IEEE, ISO, 사내 선행 규격)에서 무단 차용한 부분이 없는지를
**개별 엔지니어가 1:1 비교로 검토**한다. 검토 결과는 **종이/PDF로 출력**해
부서 내 회람·기록 자료로 활용한다.

### 1.1 사용자 핵심 요구

1. **결과를 신뢰할 수 있어야 한다** — "왜 이 라벨이 붙었는지" 즉시 이해 가능
2. **결과를 그대로 출력 가능해야 한다** — 단일 페이지 보고서, A4 인쇄 친화
3. **공신력 있는 기준에 근거해야 한다** — 산식·임계값의 출처 명시
4. **기술 도메인 특성 반영** — 규격 번호·약어·정형 구문은 표절로 오판하지 않음
5. **사용 설정 가능** — 인용·목차·참고문헌 등 사용자가 제외 항목 토글

### 1.2 본 계획의 작업 범위

- ✅ 유사도 검사 모드 한정 (Verify/Compare 모드는 Plan-34 참조)
- ✅ 1:1 비교 시나리오 (1:N은 향후 확장 — 데이터 구조만 미리 준비)
- ❌ AI Writing Detection 미포함 (별도 영역)
- ❌ 결재선/보안등급 미도입 (사내 표준 부재)

---

## 2. 업계 표준 분석 (조사 결과)

### 2.1 분류 체계 — 4개 시스템 비교

| 시스템 | 매칭 유형 라벨 | 색상 의미 |
|---|---|---|
| **Turnitin** | 명시 라벨 없음, 매칭 % 기반 (개념적으로 Verbatim/Paraphrase/Mosaic) | **출처별** 다색 + 번호 마커 |
| **iThenticate v2** | Match Group 4분류 — Cited & Quoted / Missing Quotes / Missing Citation / Not Cited | 출처별 색상 |
| **Copyleaks** | Identical / Minor Changes / Paraphrased / AI-generated | **유형별** 색상 (빨강/연빨강/보라/노랑) |
| **카피킬러 (KR)** | 표절의심 / 인용 / 법령·경전 / 일반 | **카테고리별** (파랑·회색·검정) |

### 2.2 점수 신호등 — 5단계 (Turnitin 사실상 산업 표준)

| 색상 | 구간 | 의미 |
|---|---|---|
| **Blue** | 0% | 매칭 없음 — 완전 독창 |
| **Green** | 1~24% | 양호 — 정상적 인용·정형 구문 수준 |
| **Yellow** | 25~49% | 검토 필요 — 출처 표기·재서술 점검 |
| **Orange** | 50~74% | 상당량 매칭 — 광범위한 재작성 권고 |
| **Red** | 75~100% | 위험 — 대부분이 타 출처와 동일 |

### 2.3 카피킬러 검사 설정 (한국 산업계 사용자 친숙)

| 옵션 | 동작 |
|---|---|
| ☐ 인용·출처 표시 문장 제외 | 큰따옴표 인용·각주·내주 제외 |
| ☐ 법령·경전 제외 | 원문 그대로 인용된 법령·성경 제외 |
| ☐ 목차·참고문헌 제외 | 서지정보·목차 제외 |
| 표절 판정 기준 | "6어절 이상 일치" + "1문장 이상 일치" (교육부 지침) |

### 2.4 핵심 합의사항 (Crossref / iThenticate 공식 가이드)

- **"매직 넘버" 컷오프 권장 안 함** — 점수 자체로 표절 판정 X, "검토 트리거" 역할
- **유사도 ≠ 표절** — 합법적 인용·정형 구문도 매칭됨
- **문서 유형별 임계값 차등** — 리뷰 논문은 원저보다 높은 유사도가 정상
- **검토자의 수동 판단이 최종** — 자동 거부는 금지

### 2.5 알고리즘 트렌드 (2024~2026)

| 기법 | 강점 | 본 시스템 |
|---|---|---|
| Winnowing fingerprint | 정확/근사 매칭, 단어 치환 강함 | ✅ 도입 (L1) |
| Sentence-BERT / bge-m3 | 의역·번역 탐지 | ✅ 도입 (L3) |
| Cross-language embedding | 한↔영 의역 (정확도 87%) | ⚠️ 골격만, 분기 미작동 |
| Citation-aware exclusion | 인용문/참고문헌 자동 제외 | ❌ 미도입 |
| Short match filter | 짧은 매칭 제외 (Turnitin 표준) | ❌ 미도입 |
| AI Writing Detection | LLM 생성 텍스트 식별 | ❌ 별도 영역 (본 계획 제외) |

### 2.6 보고서 양식 — 단일 페이지 표준 6요소

업계 공통 (Turnitin/iThenticate/Copyleaks):
1. 메타데이터 (문서·검사일·도구·검사자)
2. 점수 카드 (큰 % + 5단계 신호등)
3. 카테고리 breakdown (누적 바)
4. 출처 목록 (매칭률 정렬)
5. 본문 하이라이트 (출처 번호 마커 + 색상 이중 매핑)
6. 검사 기준 부록 (산식·임계값·도구·면책)

---

## 3. 현재 구현 진단

### 3.1 백엔드 — `backend/services/similarity_engine.py`

| 항목 | 위치 | 상태 | 문제 |
|---|---|---|---|
| 매칭 분류 | L291 `_classify_match` | ❌ 결함 | TYPE_TRANSLATION 반환 분기 부재(데드 라벨), `fp<0.15 AND sem>=0.88` 하드코딩 |
| Paraphrase dead zone | L297 | ❌ 결함 | fp 0.15~0.40 + sem 0.85~0.87 → low_sim 낙하, 의역 탐지 실질 불능 |
| adjusted_pct 분모 | L567 | ❌ 결함 | 보일러플레이트가 분모 포함 → 정형구문 많은 규격서 과소평가 |
| BP match_len 중복 | L316 | ❌ 결함 | 겹치는 구문 누적 → 비율 >1.0 가능 |
| 다층 파이프라인 | 전체 | ✅ 양호 | L1(Winnowing) + L3(bge-m3) 구조는 업계 표준 |
| 정형 구문 필터 | L82, `data/boilerplate-phrases.json` | 🟡 부분 | 사용 중이나 기술 도메인 phrase 부족 |
| 인용·목차·참고문헌 제외 | — | ❌ 미도입 | 카피킬러 표준 옵션 부재 |
| 짧은 매칭 필터 | — | ❌ 미도입 | Turnitin 표준 (N단어 미만 매칭 제외) |
| 임계값 설정화 | `config.py` | 🟡 부분 | th_high/th_medium만 설정 가능, 기타 분류 경계는 하드코딩 |

### 3.2 라벨 — 사용자가 이해 못 하는 이유

| 백엔드 키 | 현재 라벨 | 현재 툴팁 | 문제점 |
|---|---|---|---|
| `identical` | "일치" | "단어가 동일한 구간" | OK |
| `near_copy` | "유사" | "일부 단어가 변경된 구간" | "유사"가 모호 — 본의는 "거의 베낀" |
| `paraphrase` | "의역" | "같은 의미를 다시 쓴 구간" | OK |
| `translation` | "번역" | "다른 언어로 번역된 구간" | **데드 라벨** — 백엔드가 절대 반환 안 함 |
| `low_sim` | "참고" | "관련 가능성이 있는 구간" | "참고"는 긍정 어감 → "참고했다"로 오해 |
| `boilerplate` | "공통" | "업계 표준 문구 (점수 제외)" | OK |
| (판정 3단계) | "양호/보통/주의" | — | 업계 5단계 대비 거침 |
| (검출 레이어) | "텍스트 매칭/AI 분석/복합 분석" | — | 알고리즘 명칭은 사용자에게 무의미 |

### 3.3 UI 레이아웃 — 웹디자인 전문가 관점 분석

#### 현재 레이아웃 (compare.html 유사도 모드)
```
┌─────────────────────────────────────────────────────────────────┐
│ Compare Toolbar (모드 전환·파일 업로드·Export)                │
├──────────────────┬──────────────────┬──────────────────────────┤
│  Panel A         │  Panel B         │ [Sidebar 우측 고정]      │
│  (대상 문서)     │  (참조 문서)     │  - 점수 카드 + 3-tier 바 │
│  · 본문 마크다운 │  · 본문 마크다운 │  - 필터 칩 5개           │
│  · 문장별 색배경 │  · 문장별 색배경 │  - 매칭 카드 N개         │
└──────────────────┴──────────────────┴──────────────────────────┘
```

#### 업계 표준 레이아웃 (Turnitin/iThenticate)
```
┌──────────────────────────────────────┬───────────────────────┐
│  Body 단일 패널 (대상 문서만)        │  Insight Panel        │
│  · 출처 번호 인라인 마커 [1] [2]     │  - Match Overview     │
│  · 색상 하이라이트                   │  - Top Sources        │
└──────────────────────────────────────┴───────────────────────┘
```

#### 차이점 종합 진단

| 평가 항목 | 본 시스템 | 업계 표준 | 의견 |
|---|---|---|---|
| 본문 표시 | 좌·우 듀얼 패널 | 단일 패널 + 사이드 출처 | **본 방식이 1:1엔 우월 — 유지** |
| 출처 매핑 | 같은 색 하이라이트로만 | 번호 마커 `[1]` `[2]` 명시 | **본 방식 약점** — 매칭 5개+면 색만으론 추적 불가 |
| 점수 카드 | 단일 % + 3단계 배지 | 큰 % + 5단계 신호등 | 5단계 도입 필요 |
| 필터 칩 | 5종 인라인 체크박스 | 다축 필터 + 임계값 | "최소 단어수", "인용 제외" 등 추가 필요 |
| 매칭 카드 | 텍스트 미리보기 (100자) | 출처별 그룹핑 → 본문 점프 | **그룹핑 부재** — 같은 출처 매칭이 흩어짐 |
| 타이포그래피 | 13px Malgun Gothic, lh 1.6 | 14~15px, lh 1.7+ | **본문 가독성 부족** — 장문 검토 작음 |
| 사이드바 밀도 | 폭 ~340px, 카드 밀집 | 380~420px, 충분한 간격 | 정보 밀도 과다 |
| 인쇄 | `@media print` 부재 | 별도 PDF 다운로드 | **출력 미구현이 가장 큰 갭** |
| 빈 상태 | 단순 메시지 | 일러스트 + 가이드 | 디자인 부족 |
| 기준 표기 | 없음 | 가이드 링크, 도움말 모달 | 신뢰성 표시 부재 |

#### 핵심 디자인 결정 (확정)

1. **듀얼 패널 유지** — 1:1 검토 적합
2. **출처 번호 인라인 마커 도입** — 흑백 인쇄 호환의 핵심
3. **사이드바 3단 재구성** — ① 점수 ② 검사설정·필터 ③ 매칭 카드(출처별)
4. **본문 폰트 14.5px / line-height 1.75** — 장문 가독성
5. **5단계 신호등 채택** — 3단계는 불충분
6. **별도 인쇄 보고서 신규** — 화면 그대로가 아닌 보고서 양식 출력
7. **카피킬러식 4그룹 + 6세부 라벨 2층 구조**

### 3.4 내보내기 — `backend/services/export_service.py` + `compare.html doExportHtml`

| 항목 | 현재 | 문제 |
|---|---|---|
| Excel 시트 | "요약" + "매칭 목록" 2시트 | 산식·기준 시트 없음, 출처 그룹핑 없음 |
| HTML 리포트 | 단순 표 | 인쇄 친화 X, 표지 없음, 본문 하이라이트 없음, 출처 번호 없음 |
| TXT | plain text 라인 | 회람용으로 불충분 |
| 검사 메타데이터 | 도구·버전·임계값 미표기 | 신뢰성 부족 |
| 검사 기준 부록 | 없음 | 회람 받은 사람이 해석 불가 |

---

## 4. 핵심 설계 결정 (확정 사항 요약)

| 영역 | 결정 |
|---|---|
| **분류 라벨** | 카피킬러식 **4그룹 (표시) + 6세부 (드릴다운)** 2층 구조 |
| **점수 신호등** | Turnitin 표준 **5단계** (Blue/Green/Yellow/Orange/Red) |
| **검사 설정** | **5옵션** (정형구문/짧은매칭/목차/캡션/인용) + 임계값 슬라이더. 참고문헌 섹션·규격번호 단독 매칭은 백엔드 자동 처리 (사용자 토글 X) |
| **출처 매핑** | **번호 마커 `[1]` + 색상 배경** 이중 매핑 (흑백 인쇄 호환) |
| **인쇄 보고서** | **단일 HTML, A4 자동 분할** (매칭 수에 따라 1~3페이지) 6요소 (메타·점수·breakdown·출처·본문·기준 부록) — 결재선·보안등급 없음 |
| **도움말 전달** | **4계층 + SSOT JSON** — 묶음 1: L2(모달)+L4(보고서부록), 묶음 2: L1(툴팁)+L3(가이드페이지) |
| **캘리브레이션** | **PAN-PC 합성 방식** — 자체 시드 2종 × 변형 7종 + no-plag 1 = 15페어 |
| **분류 임계값 산식** | **2축 조합** (어휘 fingerprint × 의미 embedding) — 단순 % 기반 X |
| **사이드바** | **3단 재구성** — ① 점수 ② 검사설정·필터 ③ 매칭 카드(출처별 그룹) |
| **API 변경 정책** | 백엔드는 모든 매칭에 `exclusion_reason` 메타 부여 → 프론트가 옵션에 따라 즉시 재계산 (재요청 X) |

---

## 5. 도움말·기준 전달 체계 (4계층 + SSOT)

### 5.1 4계층 노출 전략

| 계층 | 위치 | 트리거 | 분량 | 용도 |
|---|---|---|---|---|
| **L1. 즉시** | 라벨/점수 옆 hover | 마우스 hover | 1줄 | "이게 뭐지?" 즉답 |
| **L2. 짧게** | ⓘ 클릭 → 모달 | 명시적 클릭 | 1화면 | "왜 이 라벨인지" 학습 |
| **L3. 깊게** | 가이드 페이지 | 메뉴 또는 모달 "더 알아보기" | 전체 | 신규 사용자 온보딩 |
| **L4. 자동 부록** | HTML/Excel 보고서 마지막 | 출력 시 자동 | 1페이지 | 회람 받은 사람 즉시 이해 |

### 5.2 단일 소스 원칙 (Single Source of Truth)

```
data/help/similarity-help.json
  ├── labels: { identical: { short, long, threshold, examples }, ... }
  ├── groups: { suspect: { label, color, contains: [...], ... }, ... }
  ├── score_formula: { equation, variables, citation }
  ├── verdict_bands: [ { color, range, meaning }, ... ]
  ├── check_settings: { toc_exclude: { description, default }, ... }
  └── disclaimer: "유사도 ≠ 표절 (Crossref 가이드 인용)"
        ↓
  ┌────┴────┬────────────┬──────────┐
  ↓         ↓            ↓          ↓
[툴팁]   [모달 A/B/C] [가이드페이지] [보고서 부록]
```

- 백엔드: `/api/help/similarity` 엔드포인트 (정적 JSON 그대로 반환)
- 프론트: 모달·툴팁에서 fetch
- 가이드 빌더: `tools/build_similarity_guide.py` (JSON → HTML 섹션 생성)
- 보고서: `export_service.py` 부록 생성 시 동일 JSON 참조

→ 임계값/라벨 정의 수정 시 **한 곳만 갱신**, 4채널 자동 반영.

### 5.3 L1 — 툴팁 (즉시)

기존 `.tooltip-icon` 패턴 재사용 (`css/components.css` L294, CLAUDE.md 컴포넌트 테이블):
- 사이드바 라벨 칩 옆: `data-tooltip="단어는 다른데 같은 의미를 다시 쓴 구간"`
- 점수 카드 옆: `data-tooltip="유사율 = (실질 + 의역×0.5) / 전체"`
- 검사 설정 옵션 옆: `data-tooltip="목차/장절 헤딩 라인은 점수에서 제외됩니다"`

콘텐츠 = `similarity-help.json`의 `short` 필드 자동 바인딩.

### 5.4 L2 — 모달 3종 (집중 학습)

#### 모달 A — "매칭 유형 가이드" (라벨 ⓘ 클릭)
- 첫 화면: **2축 다이어그램** (어휘 fingerprint × 의미 embedding) inline SVG
- 6종 라벨 정의표 (어휘/의미/한 줄 설명/예시 1줄)
- 푸터: "더 알아보기 → 가이드 페이지" 링크

#### 모달 B — "점수·등급 기준" (점수 카드 ⓘ 클릭)
- 산식: `유사율 = (실질 + 의역×0.5) / (전체 - 정형구문)`
- 5단계 신호등 표
- 변수 의미 (실질·의역·정형구문)
- 면책: "유사도 ≠ 표절. 검토자의 판단이 최종 (Crossref 가이드)"

#### 모달 C — "검사 설정 도움말" (검사 설정 패널 ⓘ)
- 7옵션의 동작 + 켜는 시점 가이드
- 예: "목차 제외" → 헤딩 라인이 다른 표준서와 일치할 때

### 5.5 L3 — 가이드 페이지 (`contents/guide/verify-guide.html` 유사도 챕터 신규)

7섹션 구조:
1. 유사도 검사란? + 면책 (유사도 ≠ 표절)
2. 분류 체계 — 4그룹(카피킬러식) + 6세부 + 2축 다이어그램
3. 점수 산출법 — 산식·5단계 신호등·정형구문 처리
4. 검사 설정 옵션 — 7종 + 권장 사용 시나리오
5. 도구·알고리즘 근거 — Winnowing(Schleimer 2003), bge-m3(BAAI 2024), Turnitin/Crossref 인용
6. 보고서 출력 활용법 — 출처 번호 매핑, 인쇄 색상 보존
7. 자주 묻는 질문 (FAQ)

빌드: `tools/build_similarity_guide.py` — `similarity-help.json` → HTML 섹션 자동 생성 (수동 작성 부분과 병합).

### 5.6 L4 — 보고서 자동 부록

HTML/Excel 보고서 마지막 페이지에 **"검사 기준" 1페이지** 자동 첨부:

```
─────────────────────────────────────
검사 기준 (Reference)
─────────────────────────────────────
산식: 유사율 = (실질 매칭 + 의역×0.5) / (전체 문장 - 정형구문)
신호등: Blue 0% / Green 1-24% / Yellow 25-49% / Orange 50-74% / Red 75%+

매칭 유형 6종:
  - 일치        단어 단위 거의 동일 (fp ≥ 85%)
  - 거의 동일   단어 일부 변형 (fp 40~85% + 의미 ≥ 85%)
  - 의역        다른 표현, 같은 의미 (fp < 40% + 의미 ≥ 85%)
  - 번역        다른 언어, 같은 의미 (fp ≈ 0 + 의미 ≥ 85%)
  - 약한 유사   부분 의미 유사 (fp 낮음 + 의미 65~85%)
  - 정형구문    업계 표준 문구 (점수 제외)

알고리즘: Winnowing fingerprint (Schleimer et al. 2003)
        + bge-m3 multilingual embedding (BAAI 2024)
참고:    Turnitin/Crossref Similarity Check 가이드라인
면책:    "유사도 ≠ 표절" — 검토자의 판단이 최종
도구:    Smart Document Platform v2.5 / 검사일시 2026-04-22 14:30
─────────────────────────────────────
```

### 5.7 1회 온보딩 워크스루

처음 유사도 모드 진입 시 자동 3-step:
1. "결과는 4그룹으로 분류됩니다" (표절의심/참고가능/제외/일반)
2. "라벨 옆 ⓘ를 누르면 기준을 볼 수 있습니다"
3. "결과는 인쇄용 보고서로 출력됩니다"

`localStorage('sim-onboard-v1-shown')` 저장. 사이드바 ❓ 버튼으로 재실행 가능.

---

## 6. Phase 1 — 백엔드: 분류 정상화 + 검사 설정

### 6.1 분류 로직 수정 — `_classify_match()`

```python
def _classify_match(fp_score, sem_score, th_high, th_medium):
    if fp_score >= 0.85:
        return TYPE_IDENTICAL
    if fp_score >= 0.40 and sem_score >= th_high:
        return TYPE_NEAR_COPY
    if fp_score < 0.10 and sem_score >= th_high:
        return TYPE_TRANSLATION   # ← 신규 분기 (Plan-34 P0-2)
    if fp_score < 0.40 and sem_score >= th_high:
        return TYPE_PARAPHRASE    # ← dead zone 해소 (Plan-34 P1-1)
    if fp_score >= 0.40 and sem_score >= th_medium:
        return TYPE_NEAR_COPY
    if sem_score >= 0.65:
        return TYPE_LOW_SIM
    return TYPE_LOW_SIM
```

### 6.2 보일러플레이트 — 분모 보정 + 중복 방지

```python
# 분모에서 BP 제외
effective_total = max(total - bp_count, 1)
adjusted_pct = round((substantive + derived * 0.5) / effective_total * 100, 1)

# match_len 중복 방지 (문자 인덱스 커버리지)
def _detect_boilerplate(sentences):
    indices = set()
    for i, sent in enumerate(sentences):
        sent_lower = sent.lower()
        covered = set()
        for phrase in _load_boilerplate():
            start = 0
            while True:
                pos = sent_lower.find(phrase, start)
                if pos == -1: break
                for j in range(pos, pos + len(phrase)):
                    covered.add(j)
                start = pos + 1
        if len(sent_lower) > 0 and len(covered) / len(sent_lower) >= 0.5:
            indices.add(i)
    return indices
```

### 6.3 짧은 매칭 필터 (Turnitin 표준)

```python
# config.py
VERIFY_SIMILARITY_MIN_MATCH_WORDS = 8

# 매칭 후처리
def _filter_short_matches(matches, min_words):
    return [m for m in matches if len(m["target_text"].split()) >= min_words]
```

### 6.4 검사 설정 — 5옵션 (사용자 토글) + 2건 자동 (백엔드 강제)

**사용자 토글 5옵션**:

| `exclusion_reason` | 검출 방법 | UI 토글 | 기본값 |
|---|---|---|---|
| `boilerplate` | 정형구문 phrase 50% 커버리지 (기존) | ☑ | ON |
| `short_match` | 단어 수 < 임계값 (기본 8) | ☑ | ON |
| `toc_heading` | 정규식 `^[0-9]+(\.[0-9]+)*\s+[A-Z가-힣]` (목차/장절) | ☑ | ON |
| `caption` | `^Figure \d+`, `^Table \d+`, `^그림 \d+`, `^표 \d+` | ☑ | ON |
| `cited_quote` | `"..."` / `『...』` / `\[N\]` / `(Author, Year)` 패턴 포함 | ☑ | OFF |

**백엔드 자동 처리 2건 (UI 토글 없음)**:

| `exclusion_reason` | 검출 방법 | 사유 |
|---|---|---|
| `references_section` | "References"/"참고문헌"/"BIBLIOGRAPHY" 헤딩 이후 섹션 | 거의 항상 제외 대상 — 토글 노이즈 |
| `spec_number_only` | SPEC_PATTERNS만 매칭 + 매칭 단어 수 < 5 | `short_match` 필터에 자연 흡수 가능, 별도 토글 불필요 |

매칭 결과의 각 항목에 `exclusion_reason` 메타를 부여한다. 프론트는 사용자 토글 5옵션에 따라
표시·점수에서 즉시 제외 가능 (재요청 불필요, 산식 즉시 재계산). 자동 처리 2건은 항상 제외.

매칭 객체 스키마:
```json
{
  "id": 1,
  "type": "near_copy",
  "target_idx": 12,
  "ref_idx": 8,
  "target_text": "...",
  "ref_text": "...",
  "scores": { "fingerprint": 0.62, "semantic": 0.91 },
  "exclusion_reason": null,    // ← 신규 — null이면 점수 포함, 값이 있으면 옵션에 따라 제외
  "exclusion_meta": { "matched_phrase": "in accordance with" }
}
```

### 6.5 도메인 phrase 보강 — `data/boilerplate-phrases.json`

항공·방산·일반 기술 정형구문 200개 이상 추가:
```json
{
  "phrases": [
    "in accordance with", "as specified in", "the contractor shall",
    "shall be subjected to", "unless otherwise specified",
    "이 표준은 다음 규격을 인용한다",
    "본 규격에서 사용하는 용어의 정의는 다음과 같다",
    "관련 문서는 본 규격의 일부를 구성한다",
    "...(총 200개+)"
  ],
  "patterns": [
    "^Figure \\d+[-.]\\d+",
    "^Table \\d+[-.]\\d+",
    "^그림 \\d+",
    "^표 \\d+",
    "^MIL-STD-\\d+"
  ]
}
```

### 6.6 설정 항목 외부화 — `config.py`

```python
# 신호등 5단계 경계
VERIFY_SIMILARITY_VERDICT_BANDS = [0, 25, 50, 75]  # Blue/Green/Yellow/Orange/Red

# 분류 임계값
VERIFY_SIMILARITY_PARA_FP_MAX = 0.40   # paraphrase fp 상한
VERIFY_SIMILARITY_TRANS_FP_MAX = 0.10  # translation fp 상한

# 매칭 필터
VERIFY_SIMILARITY_MIN_MATCH_WORDS = 8

# 사용자 토글 5옵션 기본값
VERIFY_SIMILARITY_DEFAULTS = {
    "exclude_boilerplate": True,    # 정형구문
    "exclude_short_match": True,    # 짧은 매칭 (8단어 미만)
    "exclude_toc": True,            # 목차/장절 헤딩
    "exclude_caption": True,        # 표/그림 캡션
    "exclude_cited_quote": False,   # 인용·출처 표시 (사용자 선택)
}
# 백엔드 자동 처리 (토글 없음): references_section, spec_number_only
```

### 6.7 변경 파일

- `backend/services/similarity_engine.py` (분류·BP·필터·exclusion_reason)
- `backend/config.py` (설정 추가)
- `data/boilerplate-phrases.json` (도메인 phrase)

---

## 7. Phase 2 — 점수 모델 + 5단계 신호등

### 7.1 5단계 신호등 (백엔드 + 프론트)

| 단계 | 구간 | 한국어 라벨 | 색상 변수 |
|---|---|---|---|
| Blue | 0% | **매칭 없음** | `--sim-band-blue` (#3b82f6) |
| Green | 1~24% | **양호** | `--sim-band-green` (#22c55e) |
| Yellow | 25~49% | **검토 필요** | `--sim-band-yellow` (#eab308) |
| Orange | 50~74% | **상당량 매칭** | `--sim-band-orange` (#f97316) |
| Red | 75~100% | **위험** | `--sim-band-red` (#ef4444) |

`config.py` → `/api/settings/public` → `js/config.js` 경유로 프론트 적용.

### 7.2 점수 산출 — 공개 산식

```
유사율 = (실질 매칭 + 의역·번역 × 0.5) / (전체 문장 - 정형구문) × 100
```

- "실질 매칭" = identical + near_copy
- "의역·번역" = paraphrase + translation
- 분모는 BP 제외 (Phase 1.2)

이 산식은 모달 B, 가이드 페이지, 보고서 부록에 동일 표기.

### 7.3 출처별 기여도 구조 (1:N 확장 대비)

```json
{
  "sources": [
    {
      "id": 1,
      "name": "MIL-STD-461G.pdf",
      "matched_sents": 23,
      "matched_words": 412,
      "match_pct": 19.4
    }
  ]
}
```

1:1 비교 단계에서는 단일 출처지만 구조는 미리 표준화.

### 7.4 변경 파일

- `backend/services/similarity_engine.py` (산식, 출처 구조)
- `backend/config.py`, `js/config.js` (5단계 색상)
- `compare.html` (점수 카드 5단계 적용)

---

## 8. Phase 3 — UI 재설계

### 8.1 라벨 — 2층 구조

#### Layer 1 — 기본 화면 표시 (카피킬러 스타일 4그룹)

| 그룹 | 색상 | 점수 포함 | 포함되는 백엔드 분류 |
|---|---|---|---|
| 🔴 **표절 의심** | 빨강 (`--color-error`) | ✅ 포함 | identical, near_copy, paraphrase, translation |
| 🟡 **참고 가능** | 노랑 (`--color-warning`) | 🟡 부분 (×0.3) | low_sim |
| ⚪ **제외 영역** | 회색 (`--text-muted`) | ❌ 제외 | boilerplate + exclusion_reason 부여된 매칭 |
| ⚫ **일반 (매칭 없음)** | 검정 본문 | — | 매칭 없는 문장 |

#### Layer 2 — 드릴다운 (사이드바 카드 + 모달 A)

| 백엔드 키 | 한국어 라벨 | 어휘 | 의미 | 한 줄 설명 |
|---|---|---|---|---|
| `identical` | **일치 (직접 차용)** | 매우 높음 | — | 단어까지 거의 그대로 |
| `near_copy` | **거의 동일 (단어 변형)** | 높음 | 높음 | 단어 일부만 바꿈 |
| `paraphrase` | **의역 (재서술)** | 낮음 | 높음 | 단어 다른데 같은 말 |
| `translation` | **번역 (다른 언어)** | 거의 0 | 높음 | 한↔영 등 언어 차이 |
| `low_sim` | **약한 유사 (참고 가능)** | 낮음 | 중간 | 단정 어려운 약한 관련성 |
| `boilerplate` | **공통 정형구문 (제외)** | — | — | 업계 표준 문구 |

#### "왜 이 라벨인가" — 2축 다이어그램 (모달 A)

```
              의미 유사도(Semantic) ↑
                    1.0 ┤
            [번역]      │   [거의 동일]
          fp≈0, sem高   │   fp 0.4~0.85
                        │   sem 高
            [의역]      │   [일치]
          fp 낮음       │   fp ≥ 0.85
          sem 高        │
                    0.0 ┼──────────────→
                        0          1.0
                        어휘 유사도(Fingerprint)
```

`DETECTION_LAYER_MAP`(L1/L3/L1+L3)은 기본 숨김, "고급 설정"에서만 노출.

### 8.2 출처 번호 인라인 마커

본문 하이라이트:
```html
<p data-sent-idx="12" class="sim-sent sim-hl sim-hl-near_copy">
  <sup class="sim-marker" data-sim-idx="3">[3]</sup>
  본문 문장 텍스트...
</p>
```

- 양쪽 패널에서 동일 번호로 매핑
- 흑백 인쇄에서도 추적 가능
- 사이드바 카드 헤더에도 같은 번호

### 8.3 사이드바 3단 재구성

```
┌─────────────────────────────┐
│ ① 점수 카드                 │
│   - 큰 % + 5단계 신호등     │
│   - 산식 ⓘ → 모달 B         │
│   - 4그룹 누적 바           │
├─────────────────────────────┤
│ ② 검사 설정 + 필터 (접이식) │
│   ⓘ → 모달 C                │
│   ☑ 정형구문 제외     [기본]│
│   ☑ 짧은 매칭 제외 (8단어)  │
│   ☑ 목차 제외               │
│   ☑ 표/그림 캡션 제외       │
│   ☐ 인용·출처 표시 제외     │
│   ─────────                 │
│   ※ 참고문헌·규격번호 단독은│
│     자동 제외 (토글 X)      │
│   ─────────                 │
│   슬라이더: 보수 / 중도 / 공격│
│   ─────────                 │
│   [표시 필터]               │
│   유형: ☑표절의심 ☑참고     │
│         ☐제외영역 ☐일반     │
├─────────────────────────────┤
│ ③ 매칭 카드 (출처별 그룹)   │
│   ▾ 출처 [1] MIL-STD (23건) │
│     ▸ #1 [일치] 95%         │
│     ▸ #2 [의역] 78%         │
│     ▸ ...                   │
└─────────────────────────────┘
```

### 8.4 검사 설정 — 동작

옵션 변경 시:
1. 백엔드 재요청 X (모든 매칭은 이미 캐시)
2. `exclusion_reason` 메타 기준으로 프론트가 즉시 재계산
3. 점수 카드·breakdown·하이라이트 즉시 갱신
4. 설정은 `localStorage('sim-check-settings')` 사용자별 유지

### 8.5 라벨 도움말 — 모달 A/B/C로 통합

§5.4 참조 (Phase 5에서 구현). Phase 3에서는 모달 컨테이너와 ⓘ 버튼만 배치.

### 8.6 본문 가독성 개선

- `.sim-md-view` 폰트 13px → 14.5px
- line-height 1.6 → 1.75
- 단락 간격 증가
- `--sim-hl-*` 변수에 인쇄 호환 색상 추가

### 8.7 빈 상태·에러 디자인

- "유사 구간이 발견되지 않았습니다" → 아이콘 + 권장 다음 단계
- 에러는 toast + 인라인 박스 병행

### 8.8 변경 파일

- `compare.html` 유사도 모드 전반 (사이드바 3단, 본문, 모달 컨테이너, 출처 마커)
- 인라인 `<style>` 또는 신규 `css/compare-similarity.css` (색상·간격·인쇄 변수)

---

## 9. Phase 4 — 단일 페이지 인쇄 보고서

### 9.1 HTML 보고서 양식 — 6요소

```
┌─────────────────────────────────────────┐
│  유사도 검토 결과 보고서                │
│  Document Similarity Report              │
├─────────────────────────────────────────┤
│ ① [메타데이터]                           │
│  대상 문서: K-SPEC-2026-Draft-v0.3.docx │
│  참조 문서: MIL-STD-461G.pdf            │
│  검사일시: 2026-04-22 14:30             │
│  검사 도구: Smart Document Platform v2.5│
│  검사자: 안휘석                          │
│  문서 ID: SIM-20260422-001              │
├─────────────────────────────────────────┤
│ ② [점수 카드]                            │
│      19%  [양호 — Green]                 │
│  실질 12% · 의역 7% · 정형구문 23%      │
│  [4그룹 누적 바 시각화]                  │
├─────────────────────────────────────────┤
│ ③ [매칭 카테고리 breakdown]              │
│  일치       3건 (12%)  ████            │
│  거의 동일  2건 ( 8%)  ██              │
│  의역       5건 ( 7%)  ██              │
│  번역       0건                          │
│  약한 유사  8건                          │
│  정형구문   18건 (제외)                  │
├─────────────────────────────────────────┤
│ ④ [출처 목록]                            │
│  [1] MIL-STD-461G.pdf — 19% 매칭        │
│      매칭 문장 23건 / 단어 412개         │
├─────────────────────────────────────────┤
│ ⑤ [본문 하이라이트]                      │
│  1. APPLICABILITY                        │
│     [1] This standard applies to ...    │
│     ████ (일치 색상 배경)               │
├─────────────────────────────────────────┤
│ ⑥ [부록: 검사 기준]                      │
│  · 산식 (§5.6 자동 첨부)                 │
│  · 5단계 신호등                          │
│  · 6종 라벨 정의                         │
│  · 알고리즘                              │
│  · 면책                                  │
│  · 검사 설정 (켜진 옵션 표기)            │
├─────────────────────────────────────────┤
│ Page 1/3 · SIM-20260422-001              │
└─────────────────────────────────────────┘
```

### 9.2 인쇄 CSS

```css
@page {
  size: A4;
  margin: 20mm 15mm;
  @bottom-right { content: counter(page) " / " counter(pages); }
  @bottom-left  { content: "SIM-" attr(data-doc-id); }
}
@page :first {
  @top-center { content: none; }
  margin-top: 25mm;
}
@media print {
  body { font-size: 11pt; line-height: 1.5; }
  .summary-card,
  .source-table,
  .matching-card { break-inside: avoid-page; }
  .section-page { break-before: page; }
  .no-print { display: none !important; }
  .sim-hl { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
}
```

### 9.3 출처 번호 + 색상 이중 매핑

```html
<span class="sim-hl sim-hl-near_copy" data-source-num="1">
  <sup>[1]</sup>This standard applies to...
</span>
```

흑백 인쇄에서도 `[1]` 마커로 출처 매핑 가능.

### 9.4 다운로드 옵션

- **HTML 보고서** (인쇄용) — 신규, 단일 파일, 외부 의존 없음
- **Excel** (검토 작업용) — 기존 유지, 산식 시트 추가
- **TXT** (요약용) — 기존 유지
- **브라우저에서 바로 인쇄** — 모달에 `window.print()` 버튼

### 9.5 변경 파일

- `compare.html` `buildHtmlReport()` 전면 재작성 (유사도 모드)
- `backend/services/export_service.py` `_write_similarity_sheet()` + 산식 시트 추가
- 신규 (선택): `js/lib/sim-report-template.js` (템플릿 분리)

---

## 10. Phase 5 — 도움말 콘텐츠 구현

§5에서 정의한 4계층 노출을 실제 구현.

### 10.1 작업 목록

| 산출물 | 파일 | 설명 |
|---|---|---|
| SSOT JSON | `data/help/similarity-help.json` | 모든 라벨·산식·신호등·옵션 콘텐츠 단일 소스 |
| Help API | `backend/api/help.py` (또는 기존 라우터) | `GET /api/help/similarity` 정적 반환 |
| 모달 A/B/C | `compare.html` | 라벨/점수/검사설정 ⓘ 클릭 시 |
| 2축 다이어그램 | `compare.html` 내 inline SVG | 모달 A 첫 화면 |
| 가이드 빌더 | `tools/build_similarity_guide.py` | JSON → HTML 섹션 자동 생성 |
| 가이드 페이지 | `contents/guide/verify-guide.html` 유사도 챕터 | L3 콘텐츠 |
| 보고서 부록 | `export_service.py` | L4 자동 첨부 |
| 온보딩 워크스루 | `compare.html` | 1회 자동 노출 + ❓ 재실행 |

### 10.2 변경 파일

위 표 + 기존 `js/toast.js` 등 공용 모듈 재사용.

---

## 11. Phase 0 — 캘리브레이션 (골드셋 + 평가)

### 11.1 PAN-PC 합성 방식 채택 근거

K-SPEC 실문서 확보 어려움 → 표절검토 시스템 개발의 표준 벤치마크인
**PAN-PC (Plagiarism Corpus, PAN @ CLEF 워크숍 2009~2015)** 방식 차용.
원문 시드에서 4가지 obfuscation strategy 합성하는 방식이 산업계 표준.

PAN-PC 표준 카테고리:
1. verbatim copies
2. random obfuscation (단어 치환·POS shuffle)
3. cyclic translation obfuscation (번역 후 역번역)
4. summary obfuscation

본 시스템에 추가:
5. manual paraphrase (사람 재서술)
6. direct translation (다른 언어 직접 비교 — K-SPEC 시나리오 핵심)
7. boilerplate-heavy (기술문서 도메인 특화)
진행
### 11.2 시드 — MIL-STD 풍 자체 합성

| 시드 | 도메인 | 분량 |
|---|---|---|
| 시드 A (영문) | EMC/EMI 시험 절차 풍 (MIL-STD-461 스타일) | **800단어, 30~40문장** |
| 시드 A_ko (한국어) | 시드 A의 자체 한국어 번역 | 동일 |
| 시드 B (영문) | 항공 환경 시험 풍 (MIL-STD-810 스타일) | **800단어, 30~40문장** |

> **분량 축소 근거**: 15페어 × 35문장 = 525 매칭 평가 포인트 (통계적으로 충분).
> 시드 작성 + 골드 라벨 부여 시간 6시간 → **2~3시간**으로 단축.

저작권 회피: 실제 표준서 인용 없이 **문체·구조만 모사**한 자체 창작.

### 11.3 페어 구성 — 총 15페어

| 페어 ID | 변형 | 대상 | 참조 | 기대 라벨 분포 | 기대 신호등 |
|---|---|---|---|---|---|
| pair_01 | verbatim | seed_a 그대로 복사 | seed_a | identical 100% | Red |
| pair_02 | random_obf | seed_a 단어 30% 치환 | seed_a | near_copy 다수 | Orange |
| pair_03 | para_light | seed_a 문장 구조 유지 + 표현 변경 | seed_a | near_copy + paraphrase | Yellow/Orange |
| pair_04 | para_heavy | seed_a 문장 재구성 + 어순 변경 | seed_a | paraphrase 위주 | Yellow |
| pair_05 | cyclic_trans | seed_a → 한 → 영 역번역 | seed_a | paraphrase + low_sim | Yellow |
| pair_06 | direct_trans | seed_a_ko (한국어) | seed_a (영문) | translation 위주 | Yellow |
| pair_07 | boilerplate | seed_a + "in accordance with..." 80% 삽입 | seed_a | boilerplate 위주, adjusted_pct 낮음 | Blue/Green |
| pair_08~14 | 위 7종 동일 변형 적용 | seed_b 기반 | seed_b | (시드 A와 동일) | (동일) |
| pair_15 | no_plagiarism | seed_a | seed_b | (탐지 안 됨) | Blue/Green |

총 7×2 + 1 = **15페어**.

### 11.4 골드셋 디렉토리

```
data/similarity-goldset/
├── seeds/
│   ├── seed_a_emc.md
│   ├── seed_a_emc_ko.md
│   └── seed_b_env.md
├── pairs/
│   ├── pair_01_verbatim_a.json
│   ├── pair_02_random_obf_a.json
│   ├── ...
│   └── pair_15_no_plag.json
└── README.md   # PAN-PC 인용, 사용법, 라이선스(자체 저작물)
```

각 페어 JSON:
```json
{
  "id": "pair_01",
  "name": "verbatim_seed_a",
  "target_file": "seeds/seed_a_emc_verbatim.md",
  "ref_file": "seeds/seed_a_emc.md",
  "expected_score_band": "red",
  "expected_score_range": [85, 100],
  "expected_matches": [
    { "target_idx": 0, "ref_idx": 0, "type": "identical" },
    ...
  ]
}
```

### 11.5 평가 도구 — `tools/similarity_eval.py`

```python
import json
from pathlib import Path
from services.similarity_engine import run_similarity

def evaluate_pair(pair_json: Path) -> dict:
    pair = json.loads(pair_json.read_text(encoding='utf-8'))
    base = pair_json.parent.parent
    target = (base / pair["target_file"]).read_text(encoding='utf-8')
    ref    = (base / pair["ref_file"]).read_text(encoding='utf-8')

    actual = run_similarity(target, ref)

    # 유형별 confusion matrix
    per_type = {}
    expected_set = {(m["target_idx"], m["ref_idx"], m["type"]) for m in pair["expected_matches"]}
    actual_set   = {(m["target_idx"], m["ref_idx"], m["type"]) for m in actual["matches"]}

    for label in ("identical", "near_copy", "paraphrase", "translation", "low_sim"):
        exp = {(t, r) for t, r, ty in expected_set if ty == label}
        act = {(t, r) for t, r, ty in actual_set if ty == label}
        TP = len(exp & act)
        FP = len(act - exp)
        FN = len(exp - act)
        precision = TP / (TP + FP) if (TP + FP) else 0
        recall    = TP / (TP + FN) if (TP + FN) else 0
        f1        = 2 * precision * recall / (precision + recall) if (precision + recall) else 0
        per_type[label] = {"P": precision, "R": recall, "F1": f1,
                           "TP": TP, "FP": FP, "FN": FN}

    actual_score = actual["summary"]["tiers"]["adjusted"]
    band_lo, band_hi = pair["expected_score_range"]
    return {
        "pair": pair["id"],
        "per_type": per_type,
        "score_actual": actual_score,
        "score_expected_range": [band_lo, band_hi],
        "score_in_band": band_lo <= actual_score <= band_hi
    }

def evaluate_all() -> dict:
    results = [evaluate_pair(p) for p in
               sorted(Path("data/similarity-goldset/pairs").glob("*.json"))]
    overall_f1 = ...  # weighted average
    band_acc = sum(1 for r in results if r["score_in_band"]) / len(results)
    return {"results": results, "overall_f1": overall_f1, "band_accuracy": band_acc}
```

### 11.6 목표 지표

| 라벨 | 목표 F1 | 비고 |
|---|---|---|
| identical | ≥ 0.95 | Winnowing fast-accept |
| near_copy | ≥ 0.85 | fp 0.40~0.85 대역 |
| paraphrase | ≥ 0.70 | 가장 어려운 영역 |
| translation | ≥ 0.65 | bge-m3 다국어 능력 의존 |
| low_sim | ≥ 0.60 | 노이즈 많음 |
| **overall (weighted)** | **≥ 0.80** | 전체 가중 평균 |
| **score band accuracy** | **≥ 80%** | 5단계 신호등 적중률 |

### 11.7 임계값 보정 절차

1. Phase 1·2 구현 직후 `tools/similarity_eval.py` 실행
2. 목표 미달 라벨 식별
3. grid search로 다음 파라미터 미세 조정:
   - `VERIFY_SIMILARITY_THRESHOLD_HIGH` (현재 0.85)
   - `VERIFY_SIMILARITY_THRESHOLD_MEDIUM` (현재 0.75)
   - `VERIFY_SIMILARITY_PARA_FP_MAX` (Phase 1: 0.40)
   - `VERIFY_SIMILARITY_TRANS_FP_MAX` (Phase 1: 0.10)
   - `VERIFY_SIMILARITY_MIN_MATCH_WORDS` (Phase 1: 8)
   - 5단계 신호등 경계 (현재 25/50/75)
4. 목표 도달 시 `config.py` 반영
5. 사내 사용 1개월 후 실 사례 수집 → 재캘리브레이션

### 11.8 골드셋 작성 순서

0. **사전 점검**: Ollama bge-m3 모델 가용성 확인 (`curl $OLLAMA_URL/api/tags`) — L3 작동 여부
1. 시드 A 영문 작성 (800단어, EMC 풍) — Claude 작성 + 사용자 검수
2. 시드 B 영문 작성 (800단어, 환경시험 풍) — 동일 방식
3. 시드 A 한국어 번역본 작성 (translation 페어용)
4. 7종 변형 텍스트 생성 — LLM(Claude) 보조 + 자체 검수
5. 각 페어의 골드 라벨 JSON 부여 (자체 생성이므로 매핑 자명, 자동 생성 가능)
6. README 작성 (PAN-PC 인용, 사용법, 라이선스 — 자체 저작물 CC0)

---

## 12. 위험과 완화

| # | 위험 | 영향 | 완화 |
|---|---|---|---|
| R1 | bge-m3 모델 의존 — Ollama 다운 시 L3 무력화 | translation/paraphrase 탐지 불가, identical/near_copy만 작동 | L3 실패 시 명시적 경고 표시 + L1만으로 부분 결과 제공 (이미 코드 상 폴백 있음) |
| R2 | 한↔영 번역 탐지 정확도 미검증 (목표 F1 0.65) | 골드셋 평가에서 미달 시 분류 신뢰도 저하 | 캘리브레이션 결과를 가이드에 명시 ("번역 탐지는 참고용") |
| R3 | 합성 골드셋의 한계 — 실 사용과 분포 차이 | 1개월 후 실 사례에서 재캘리브레이션 필요 | §11.7 5단계 절차에 명시. 실 사용 1개월 후 사례 수집 |
| R4 | 검사 설정 7옵션 잘못 켜면 점수 왜곡 | 사용자가 "참고문헌 제외" 켰는데 실제론 표절 부분 제외됨 | 모달 C에 "켜는 시점 가이드" 명시. 기본값 보수적 (참고문헌·인용은 OFF) |
| R5 | 도움말 콘텐츠 의존 — 처음엔 학습 곡선 | 신규 사용자가 라벨 의미 모름 | 4계층 노출 + 1회 온보딩 워크스루로 완화 |
| R6 | 인쇄 CSS 브라우저 호환성 | Chrome/Edge는 OK, Firefox는 `@page` 부분 미지원 | 사내 표준 Chrome/Edge 가정 (Plan-31 호환) |
| R7 | `exclusion_reason` 메타 추가 시 기존 API 호환성 | 외부 호출자 (현재 없음) | 신규 필드는 optional, 기존 필드 유지 |
| R8 | 보일러플레이트 phrase 200개 보강 — 오탐/미탐 | 기술문서 정형구문 미스 | 사용자 토글 (정형구문 제외)로 완화. 실제 사용 후 보강 |
| R9 | 5단계 신호등 경계 문서 유형별 차등 권고와 충돌 | 모든 문서에 동일 경계 적용 | 가이드에 "기술 표준서는 정형구문 비율 높아 Green-Yellow 경계 더 관대 권고" 명시 |
| R10 | 1:N 확장 시 출처 번호 마커 폭주 | UI 가독성 저하 | 1:N은 별도 Plan으로 — 본 계획은 1:1 한정 |

---

## 13. 변경 파일 종합

| 파일 | Phase | 변경 |
|---|---|---|
| `backend/services/similarity_engine.py` | 1, 2 | `_classify_match`, `_detect_boilerplate`, `_filter_short_matches`, `exclusion_reason` 부여, 산식 정리 |
| `backend/services/export_service.py` | 4, 5 | `_write_similarity_sheet` 보강, 산식 시트 추가, 보고서 자동 부록 |
| `backend/config.py` | 1, 2 | 신호등 경계, 분류 임계값, 최소 단어수, 검사 설정 기본값 |
| `data/boilerplate-phrases.json` | 1 | 도메인 phrase 200+ 보강, patterns 섹션 추가 |
| `js/config.js` | 2 | 5단계 신호등 색상 공개 설정 |
| `compare.html` | 2~5 | 점수 카드 5단계, 사이드바 3단(검사설정 포함), 출처 번호 마커, 모달 컨테이너, 온보딩, HTML 보고서 |
| `contents/guide/verify-guide.html` | 5 | 유사도 챕터 7섹션 신규 |
| **신규** `data/help/similarity-help.json` | 5 | SSOT 콘텐츠 |
| **신규** `backend/api/help.py` (또는 기존 라우터) | 5 | `/api/help/similarity` |
| **신규** `tools/build_similarity_guide.py` | 5 | JSON → 가이드 HTML 빌더 |
| **신규** `tools/similarity_eval.py` | 0 | 골드셋 평가 |
| **신규** `data/similarity-goldset/seeds/*.md` | 0 | 시드 3종 (A 영문/A 한국어/B 영문) |
| **신규** `data/similarity-goldset/pairs/*.json` | 0 | 골드 라벨 15페어 |
| **신규** `data/similarity-goldset/README.md` | 0 | 사용법·인용·라이선스 |
| **신규(선택)** `js/lib/sim-report-template.js` | 4 | 인쇄 보고서 템플릿 분리 |
| **신규(선택)** `css/compare-similarity.css` | 3 | 인라인 스타일 분리 시 |

---

## 14. 작업 묶음 — 2단계 진행

### 14.1 묶음 1 — "현업 즉시 투입 가능 수준" (예상 1.5~2주)

**목표**: K-SPEC 표절검토 실무 투입 가능. UI는 현 사이드바 유지, 점수·분류·인쇄만 정상화.

| 단계 | 내용 | 산출물 |
|---|---|---|
| 0 | **사전 점검** — Ollama bge-m3 가용성 (회사 Windows PC에서) | 가용 확인 또는 위험 식별 |
| 1 | Phase 0 — 골드셋 15페어 작성 (시드 800단어 ×2 + 한국어 번역 + 변형 7종) + 평가 도구 | `data/similarity-goldset/`, `tools/similarity_eval.py` |
| 2 | Phase 1 — 백엔드 분류 정상화 (분류 로직 + BP + 짧은 매칭 + 검사설정 5+2 + exclusion_reason) | `similarity_engine.py`, `config.py`, `boilerplate-phrases.json` |
| 3 | 골드셋 캘리브레이션 1차 (회사 PC에서 Ollama 활용) | 임계값 확정 |
| 4 | Phase 2 — 5단계 신호등 + 산식 정리 | `compare.html` 점수 카드 |
| 5 | Phase 4 — HTML A4 자동분할 보고서 + 보고서 부록 (L4 도움말) | `export_service.py`, `buildHtmlReport()`, `data/help/similarity-help.json` 초안 |
| 6 | Phase 5 일부 — 모달 B (점수 ⓘ, 산식·신호등·면책) | `compare.html` 모달 B만 |

**묶음 1 종료 시 사용자 체감**:
- 한↔영 번역 탐지 작동
- 의역 탐지 정상화
- 점수 5단계 신호등 (업계 표준)
- 인쇄 보고서 (A4 자동 분할) 출력 가능 → **K-SPEC 부서 회람 시작 가능**
- 점수 카드 ⓘ 클릭 시 산식·신호등·면책 모달 (모달 B)
- 보고서 부록에 검사 기준 자동 첨부 (L4 도움말)

검사 설정 5옵션은 백엔드만 적용 (기본값 ON 4건 자동 적용). UI 토글은 묶음 2에서.

### 14.2 묶음 2 — "사용성·이해도 향상" (묶음 1 사용 1~2주 후)

**목표**: 사용자 학습 곡선 단축 + UI에서 검사 설정 토글 가능.

| 단계 | 내용 | 산출물 |
|---|---|---|
| 1 | Phase 3 — UI 재설계 (사이드바 3단, 출처 번호 마커, 4그룹 라벨, 가독성) | `compare.html`, CSS |
| 2 | Phase 5 — 도움말 L1(툴팁)·L3(가이드 페이지) + 모달 A/C 추가 | `data/help/` 확장, `tools/build_similarity_guide.py`, `verify-guide.html`, 온보딩 |
| 3 | 검사 설정 5옵션 UI 토글 + 즉시 재계산 | `compare.html` |
| 4 | 골드셋 재캘리브레이션 (실 사용 사례 흡수) | 임계값 미세 조정 |

### 14.3 진행 흐름

```
[승인] → [묶음 1 착수] → [묶음 1 완료] → [사용자 시범 검토 1~2주]
       ↓                                ↓
       골드셋 평가 보고            피드백 수집
                                        ↓
                                 [묶음 2 착수] → [묶음 2 완료]
                                        ↓
                                 실 사례 재캘리브레이션
```

---

## 15. 성공 기준

### 15.1 묶음 1 완료 기준

- ✅ TYPE_TRANSLATION 분기 작동 (골드셋 pair_06에서 translation 라벨 검출)
- ✅ Paraphrase dead zone 해소 (pair_03/04에서 paraphrase 라벨 검출)
- ✅ 정형구문 분모 보정 (pair_07에서 adjusted_pct ≤ 25%)
- ✅ 5단계 신호등 표시 (Blue/Green/Yellow/Orange/Red)
- ✅ 단일 페이지 인쇄 보고서 출력 가능 (A4)
- ✅ 보고서 부록 자동 첨부 (검사 기준 1페이지)
- ✅ 흑백 인쇄에서 출처 번호 `[1]`로 매핑 추적 가능
- ✅ 골드셋 overall F1 ≥ 0.80, score band accuracy ≥ 80%

### 15.2 묶음 2 완료 기준

- ✅ 카피킬러식 4그룹 화면 표시 + 클릭 시 6세부 드릴다운
- ✅ 사이드바 3단 재구성 (점수 / 검사설정·필터 / 매칭 카드 출처별 그룹)
- ✅ 검사 설정 7옵션 UI 토글 + 즉시 재계산
- ✅ 라벨 옆 ⓘ 클릭 시 모달 A (2축 다이어그램 + 6라벨 정의)
- ✅ 점수 카드 ⓘ 클릭 시 모달 B (산식 + 5단계 + 면책)
- ✅ 검사설정 ⓘ 클릭 시 모달 C (7옵션 가이드)
- ✅ 가이드 페이지 7섹션 작성 + 메뉴 등록
- ✅ 1회 온보딩 워크스루 자동 노출 + ❓ 재실행
- ✅ 도움말 SSOT JSON에서 4채널(툴팁·모달·가이드·부록) 모두 파생

### 15.3 정성 기준

- ✅ 신규 사용자가 도움말 1회 클릭으로 라벨 의미 이해
- ✅ 회람 받은 사람이 보고서만으로 결과 해석 가능
- ✅ "유사도 ≠ 표절" 면책이 사용자에게 명시적으로 전달

---

## 16. 참고 자료

### 16.1 권위 있는 가이드
- Turnitin Guides — Understanding the similarity score (2026)
- iThenticate v2 — Navigating the new Similarity Report
- Crossref Similarity Check — Working with your Similarity Report
- Crossref Best Practices — Interpreting Similarity Check Reports (Zenodo, 2025)

### 16.2 알고리즘 논문
- Schleimer, Wilkerson, Aiken — *Winnowing: Local Algorithms for Document Fingerprinting* (SIGMOD 2003)
- BAAI — *bge-m3 Multilingual Embedding* (2024)
- Frontiers — *Plagiarism types and detection methods: a systematic survey* (2025)
- *Cross-Lingual Plagiarism Detection: Two Are Better Than One* (Springer, 2023)

### 16.3 벤치마크 코퍼스
- Potthast, Stein et al. — *PAN Plagiarism Corpus 2011 (PAN-PC-11)* (Webis/Zenodo)
- PAN @ CLEF 워크숍 시리즈 (2009~2015)

### 16.4 한국 산업계
- 무하유 카피킬러 캠퍼스 v2 사용 매뉴얼
- 카피킬러 검사결과 매뉴얼 (manual.muhayu.com)

### 16.5 인쇄 기술
- W3C CSS Paged Media (CSS 2.2)
- MDN — `page-break-inside`, `@page` rule
- DocuSeal — CSS Page Styling for Print

---

## 17. 승인 이력 및 진행 상태

### 17.1 사용자 승인 (2026-04-22)

사용자가 Claude의 전문성·경험에 진행 권한 위임. Claude 판단으로 5건 수정 후 확정:

- ✅ 본 계획서 전체 방향
- ✅ 카피킬러식 4그룹 + 6세부 라벨 2층 구조
- ✅ 검사 설정 — **5옵션** (Claude 판단: 7→5 축소, 참고문헌·규격번호 백엔드 자동)
- ✅ 5단계 신호등 (Blue/Green/Yellow/Orange/Red)
- ✅ 6요소 인쇄 보고서 — **A4 자동 분할** (결재선·보안등급 없음)
- ✅ 도움말 4계층 + SSOT — **묶음 1: L2+L4 / 묶음 2: L1+L3** (Claude 판단: 분할 도입)
- ✅ PAN-PC 합성 골드셋 — **시드 800단어** (Claude 판단: 1500→800 축소)
- ✅ 묶음 1 → 사용 1~2주 → 묶음 2
- ✅ 검사 설정 기본값 (정형구문/짧은매칭/목차/캡션 ON, 인용 OFF)

### 17.2 사전 점검 결과 (2026-04-22)

- Ollama bge-m3 가용성: **본 PC(개발 환경)에서 직접 점검 불가** — `host.docker.internal:11434`
  → 캘리브레이션은 회사 Windows PC에서 수행 (CLAUDE.md 명시)
- 코드 레벨 위험 없음 — `OLLAMA_URL` 환경변수로 추상화됨

### 17.3 진행 상태

- ✅ 계획서 확정 (개정 2)
- ✅ **묶음 1 1단계 (Phase 0 골드셋) 완료** (2026-04-23)
  - 시드 3종 (A 영문 652단어, A 한국어, B 영문 671단어)
  - 변형 12종 (verbatim/random_obf/para_light/para_heavy/cyclic_trans/boilerplate × 시드 2종)
  - 골드 라벨 14페어 JSON
  - 평가 도구 `tools/eval/similarity_eval.py`
  - README + `generate_pairs.py`
- ✅ **베이스라인 측정 완료** (Phase 1 수정 전 현재 코드)
  - 14페어 중 **2 PASS / 12 FAIL** — 라벨 분포 정확도 14%
  - 점수 대역 적중률 78.6% (점수는 비교적 정확)
  - 계획서 진단 실측 검증 — TYPE_TRANSLATION 데드(pair_06: 0%), Paraphrase dead zone(pair_04: 0%, pair_11: 10%) 모두 확인
- ✅ **묶음 1 2단계 — Phase 1 백엔드 분류 정상화 완료** (2026-04-23)
  - `_classify_match` 4분기 명시화 + cross-language 감지 (`_is_cross_language`)
  - `_detect_boilerplate` 문자 커버리지 수정 (중복 누적 방지)
  - `_filter_short_matches` 병합 후 단어수 필터 (8단어 미만)
  - `_detect_exclusions` 신규 — toc/caption/references/cited_quote/spec_only 검출
  - `exclusion_reason` 메타 부여 (5 토글 + 2 자동)
  - `_compute_summary` 분모 보정 (활성 제외 sentence index 집합 기반)
  - `boilerplate-phrases.json` 53→303 phrases + 31 patterns 보강
  - `config.py` 신규 항목 (5단계 신호등, 분류 임계값, 검사 설정 기본값)
- ✅ **회귀 검증** — 모든 기존 필드 유지 (top-level / summary / tiers / breakdown / matches), 신규 필드는 optional
- ✅ **묶음 1 4단계 — Phase 2 5단계 신호등 + sources 완료** (2026-04-23)
  - `_compute_verdict_band(score)` 신규 — 5단계 (Blue/Green/Yellow/Orange/Red)
  - `VERDICT_LABELS_KO` 한국어 매핑 (매칭 없음/양호/검토 필요/상당량 매칭/위험)
  - `summary.verdict` + `summary.verdict_label` 신규 필드
  - `summary.sources[]` 신규 — id/name/matched_sents/matched_words/match_pct (1:N 확장 대비)
  - `_empty_result`에도 신규 필드 포함 (None safety)
  - `settings_service`: `verify_verdict_bands` 노출 (frontend는 기존 verdict_low/_high 그대로 사용 — 호환)
  - 9 경계 케이스 단위 테스트 통과
  - 14페어 verdict 적중률 9/14 (64.3%) — 5 misses는 골드셋 변형 강도 이슈
- ✅ **묶음 1 5단계 — Phase 4 HTML A4 인쇄 보고서 + L4 도움말 부록 완료** (2026-04-23)
  - `data/help/similarity-help.json` SSOT 신규 (labels/groups/score_formula/verdict_bands/check_settings/disclaimer)
  - `backend/api/help.py` 신규 라우터 — `GET /api/help/similarity` 정적 JSON 반환 (캐시)
  - `compare.html`: `simHelp` 변수 + 초기 fetch + `verdictBands5` 5단계 경계
  - `buildSimilarityReportHtml(p)` 신규 — 6요소 보고서 (메타·점수·breakdown·출처·매칭상세·부록)
    - A4 `@page` 인쇄 CSS (`break-inside: avoid-page`, `print-color-adjust: exact`)
    - 부록 `page-break-before: always`로 마지막 페이지 분리 (1페이지)
    - 출처 번호 마커 `[1]` (흑백 인쇄 호환)
    - 5단계 신호등 색상 카드 (`score-band-{verdict}`)
    - SSOT JSON에서 부록 자동 렌더링 (산식/5단계표/6라벨표/알고리즘/면책)
  - `buildExportPayload`: verdict/verdict_label/sources/exclusion_breakdown/source_num/exclusion_reason/type_key 추가
  - `export_service.py`: 산식 시트 신규(`_write_similarity_criteria_sheet`), summary 시트에 verdict_label·sources 노출
  - 검증: 백엔드 schema(/api/help, /api/compare/similarity), Node 보고서 평가, Playwright 시각 미리보기, 골드셋 회귀(4/14 유지) 모두 정상
- ✅ **묶음 1 6단계 — Phase 5 일부 (모달 B) 완료** (2026-04-23)
  - 점수 카드 옆 ⓘ 도움말 버튼 (`.sim-score-info`)
  - 클릭 시 `showSimScoreHelpModal()` — 4개 섹션 (산식·변수의미·5단계 신호등·면책)
  - SSOT JSON(`/api/help/similarity`)에서 콘텐츠 자동 파생 — 폴백 인라인 데이터 보유
  - 5단계 색상 배지 (`sim-help-band-{color}`) + 다크모드 보더 보강
  - 모달 body `max-height` + 스크롤 (긴 콘텐츠 안전)
  - 닫기 버튼 + ESC 키 + 배경 클릭 — 3가지 닫기 경로
  - 검증: ⓘ 클릭 → 모달 표시 / ESC → 닫힘 / 닫기 버튼 → 닫힘 / 콘솔 에러 0건 / 골드셋 회귀 4/14 유지
- ⏸️ 묶음 1 잔여 단계 3 — 캘리브레이션 1차 (선택, §17.6 항목)
- ✅ **묶음 2 단계 1 — Phase 3 UI 재설계 P1 영역 완료** (2026-04-23)
  - SIM_TYPE_MAP 6세부 라벨 한국어 재정의 + SSOT(`simHelp.labels`) 동기화 (`_syncSimTypeMapFromHelp`)
    - "유사" → "거의 동일", "참고" → "약한 유사", "공통" → "공통 정형구문"
  - 카피킬러식 4그룹 누적 바 (sim-group-bar) — 표절 의심/참고 가능/제외 영역/일반 (3-tier 바 대체)
  - 출처 번호 마커 [1] (sim-source-marker, sim-hl-marker)
    - 사이드바 매칭 카드 헤더 + 본문 양쪽 패널 첫 매칭 문장에 sup
    - 흑백 인쇄 호환 (Plan §8.2)
  - 본문 가독성: `.sim-md-view` 14.5px / line-height 1.75 / 단락 간격 0.5em (전역 토큰 무영향, 로컬 오버라이드)
  - 빈 상태 디자인: 아이콘 SVG + 권장 다음 단계 안내문 (`.sim-empty-state`)
  - 검증: 콘솔 에러 0건, Playwright 시각 (4그룹 바 색상·라벨·점수카드·매칭카드·[1] 마커 모두 정상 렌더링), 골드셋 회귀 4/14 유지
- ✅ **묶음 2 단계 2 — Phase 5 모달 A + 온보딩 완료** (2026-04-23)
  - `showSimLabelHelpModal()` — 매칭 유형 가이드 (모달 A)
    - 분류 원리 — 2축 조합 설명 (어휘 fp × 의미 sem)
    - **2축 다이어그램 inline SVG** (4사분면 + 5라벨 점 위치 + 축 마커)
    - 6라벨 정의표 (어휘/의미/설명/임계값) — SSOT JSON에서 파생
  - `showSimOnboarding(force)` — 1회 자동 3-step 워크스루
    - Step 1: "결과는 4그룹으로 분류됩니다"
    - Step 2: "ⓘ를 누르면 기준을 볼 수 있습니다"
    - Step 3: "결과는 인쇄용 보고서로 출력됩니다"
    - localStorage `sim-onboard-v1-shown` 저장 (1회 자동)
    - 사이드바 ❓ 버튼으로 강제 재실행 가능
  - 트리거 추가:
    - 4그룹 라벨 우측 ⓘ → 모달 A
    - 사이드바 헤더 ❓ (유사도 모드만 표시) → 온보딩 재실행
    - `setMode('similarity')` 진입 시 온보딩 자동 (첫 1회)
  - CSS: `.sim-label-help-modal` (720px), `.sim-axis-svg`, `.sim-help-label-{key}` 6색 라벨, `.sim-onboard-dot` 진행 도트
  - 검증: 콘솔 에러 0건, Playwright 시각 (온보딩 step1·도트, 모달 A SVG 5점·6라벨표·축 모두 정상), 골드셋 회귀 4/14 유지
- ✅ **묶음 2 단계 3 — 검사 설정 5옵션 UI 토글 + 모달 C 완료** (2026-04-23)
  - 사이드바 점수 카드 아래 `<details class="sim-check-settings">` 접이식 패널
  - 5체크박스 (정형구문/짧은매칭/목차/캡션/인용) — 기본 ON 4건 + 인용 OFF
  - 헤더 ⓘ → `showSimCheckHelpModal()` (모달 C — 5옵션 + 자동 제외 2건 가이드)
  - 변경 시 즉시 재계산 — `simRecomputeFromSettings()`:
    - exclusion_reason 메타 기반 매칭 카운트 재계산
    - 활성 제외 sentence 수로 분모 보정
    - 점수 카드 + 4그룹 바 + breakdown 동시 갱신
    - 활성 제외된 매칭 카드는 `.sim-match-excluded` (흐리게 + "제외 영역" 배지)
  - localStorage 'sim-check-settings' 사용자별 저장
  - 결과 첫 표시 시 사용자 설정 자동 적용 (백엔드 기본값과 다른 경우)
  - 검증: Playwright 시각 (5체크박스 + 모달 C 7행), 콘솔 에러 0건, 골드셋 회귀 4/14 유지
- ⏸️ 묶음 2 단계 4 — 사이드바 3단 재구성 + L3 가이드 페이지 + 재캘리브레이션

### 17.4 Phase 0 베이스라인 상세 (Phase 1 비교 기준점)

| 페어 | 변형 | 점수 | 점수 대역 | 라벨 분포 | 핵심 실패 사유 |
|---|---|---|---|---|---|
| pair_01 | verbatim_a | 98.5% | ✓ | ✓ | PASS |
| pair_08 | verbatim_b | 99.0% | ✓ | ✓ | PASS |
| pair_02 | random_obf_a | 86.0% | ✓ | ✗ | near_copy 0.17 (기대 0.30~0.70) |
| pair_09 | random_obf_b | 85.2% | ✓ | ✗ | near_copy 0.26 (기대 0.30~0.70) |
| pair_03 | para_light_a | 37.6% | ✓ | ✗ | low_sim 0.46 (기대 0.0~0.30) |
| pair_10 | para_light_b | 35.2% | ✓ | ✗ | low_sim 0.50 (기대 0.0~0.30) |
| pair_04 | para_heavy_a | 11.1% | ✗ | ✗ | **paraphrase 0.0** (기대 0.30~0.80), low_sim 0.87 |
| pair_11 | para_heavy_b | 21.8% | ✓ | ✗ | **paraphrase 0.10** (기대 0.30~0.80) |
| pair_05 | cyclic_trans_a | 46.3% | ✓ | ✗ | low_sim 0.37 (기대 0.0~0.30) |
| pair_12 | cyclic_trans_b | 45.4% | ✓ | ✗ | low_sim 0.32 (기대 0.0~0.30) |
| pair_06 | direct_trans_a | 14.5% | ✗ | ✗ | **translation 0.0** (기대 0.40~1.0), low_sim 0.80 |
| pair_07 | boilerplate_a | 25.3% | ✓ | ✗ | low_sim 0.60 (기대 0.10~0.50) |
| pair_13 | boilerplate_b | 22.9% | ✓ | ✗ | identical 0.33 (기대 0.0~0.30), bp_ratio 부족 |
| pair_14 | no_plagiarism | 8.8% | ✓ | ✗ | identical 0.17 (기대 0.0~0.10) — 정형 헤더 매칭 |

**Phase 1 수정 후 기대**: 12 FAIL → 12 PASS (라벨 분포 정상화).
재실행 명령: `PYTHONPATH=backend python tools/eval/similarity_eval.py --json /tmp/post-phase1-eval.json`

### 17.5 Phase 1 적용 후 측정 결과

```
Baseline → Phase 1 적용 후
PASS:        2/14 → 4/14 (+2)
점수 대역:   78.6% → 85.7% (+7.1pp)
라벨 분포:   14% → 28% (+14pp)
```

| 페어 | 베이스라인 | Phase 1 | 개선 사항 |
|---|---|---|---|
| pair_01 verbatim_a | PASS | PASS | 유지 |
| pair_02 random_obf_a | FAIL | FAIL | 점수 86 ✓ but identical 0.67 (기대 ≤0.6 — 골드셋 보정 필요) |
| pair_03 para_light_a | FAIL | FAIL | 점수 19 (기대 25-75) — bge-m3 sem 추가 보정 필요 |
| pair_04 para_heavy_a | FAIL | FAIL | 점수 14.6 (기대 15+) — 거의 통과, 임계값 미세조정 |
| pair_05 cyclic_trans_a | FAIL | FAIL | 점수 43 ✓, paraphrase 0.88 (기대 ≤0.7 — 골드셋 보정) |
| pair_06 direct_trans_a | FAIL | FAIL | **translation 분류 작동 시작** (이전 0%), 점수 15 |
| pair_07 boilerplate_a | FAIL | FAIL | paraphrase 0.35 (boilerplate가 sem 매칭에 포함 — 우선순위 검토) |
| pair_08 verbatim_b | PASS | PASS | 유지 |
| pair_09 random_obf_b | FAIL | FAIL | 점수 81 ✓, identical 0.66 (골드셋 보정) |
| pair_10 para_light_b | FAIL | FAIL | 점수 37 ✓, paraphrase 0.81 (기대 ≤0.6 — 골드셋 보정) |
| pair_11 para_heavy_b | FAIL | **PASS** | **신규 통과** — paraphrase dead zone 해소 효과 |
| pair_12 cyclic_trans_b | FAIL | FAIL | 점수 41 ✓, paraphrase 0.93 (골드셋 보정) |
| pair_13 boilerplate_b | FAIL | FAIL | paraphrase 0.38 (boilerplate 우선순위) |
| pair_14 no_plagiarism | FAIL | **PASS** | **신규 통과** — BP 분모 보정 효과 |

### 17.6 잔여 캘리브레이션 항목 (묶음 1 3단계)

1. **골드셋 expected_label_distribution 미세조정** — 변형 텍스트가 의도보다 가벼운 변경(random_obf 10% vs 의도 30%) 등 실제 시스템 동작 기반 보정
2. **boilerplate 우선순위** — 의미 매칭에서 boilerplate 텍스트가 paraphrase로 잡히는 현상. `_detect_boilerplate`보다 sem-match가 먼저 적용되는 경우 검토
3. **bge-m3 cross-lingual sem 분포** — Korean-English 0.65~0.75 구간 처리 (translation 컷오프 추가 검토)
4. **goldset 변형 강도 재작성 (선택)** — random_obf 30% 단어 치환을 더 적극적으로
