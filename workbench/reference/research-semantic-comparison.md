# 한국어 기술문서 의미비교 — 연구 주제 정리

> 작성일: 2026-03-15
> 상태: 아이디어 단계 (추후 진행 검토)
> 관련 시스템: Smart Document Platform — Compare 시스템 Phase 6

---

## 1. 연구 배경

### 1.1 문제 정의

기술문서(항공, 방산, SW 아키텍처 등) 개정 시, 텍스트 diff 도구는 **"무엇이 바뀌었는지"**만 보여준다. 그러나 실무에서 검토자가 필요로 하는 정보는 **"왜, 얼마나 중요한 변경인지"**이다.

예시:

| diff 결과 (현재) | 검토자가 실제로 알고 싶은 것 |
|-----------------|---------------------------|
| "서버" → "Server" | 용어 변경일 뿐, 의미 동일 (편집 변경) |
| "100ms 이내" → "200ms 이내" | 성능 요구사항 완화 — 검토 필요 |
| 문장 순서만 바뀜 | 구조 재배치, 의미 동일 |
| 문장이 완전히 다른 내용으로 교체 | 의미 변경 — 반드시 검토 필요 |

### 1.2 시장 공백

- AI 기반 문서 비교 도구는 **영어 법률문서** 도메인에 집중 (Litera, Spellbook, BlackBoiler, Luminance 등)
- **한국어 기술문서**에 특화된 의미비교 도구는 시장에 존재하지 않음 (2026-03 조사 기준)
- CJK 언어 + 기술문서 도메인 + 로컬 LLM 조합의 선행 연구 부재

### 1.3 기존 시스템 활용

Smart Document Platform의 Compare 시스템이 Phase 1~5까지 구현 완료 상태:
- Phase 2: jsdiff 기반 텍스트 비교 (단어 수준 하이라이트)
- Phase 3: 규칙 기반 검증 (금지 용어, 용어 일관성, 문장 길이 등)
- Phase 4: 수락/거절 + 내보내기
- Phase 5: CSV/JSON 규칙 관리

**→ 이 위에 LLM 의미 분류 레이어만 추가하면 연구 시스템이 완성됨**

---

## 2. 연구 주제

### 2.1 논문 제목 (안)

**국문**: 로컬 LLM을 활용한 한국어 기술문서 개정 변경의 의미 분류 — 항공 소프트웨어 문서 사례

**영문**: Semantic Classification of Revision Changes in Korean Technical Documents Using Local LLMs — A Case Study on Aviation Software Documentation

### 2.2 핵심 연구 질문

1. 로컬 LLM(Ollama)이 한국어 기술문서 변경 구간의 의미 분류를 얼마나 정확하게 수행할 수 있는가?
2. 규칙 기반 분류 대비 LLM 기반/하이브리드 접근의 정확도와 비용(시간) 트레이드오프는?
3. 의미 분류 제공이 검토자의 문서 검토 시간과 판단 정확도에 미치는 영향은?

### 2.3 학술적 기여 (Contribution)

1. **한국어 기술문서 변경 분류 체계 제안** — fda-guidance-diff의 영문 규제문서용 8종 태그를 한국어 기술문서에 맞게 적응
2. **로컬 LLM 기반 분류 파이프라인** — 폐쇄망(항공/방산) 환경에서 운용 가능한 아키텍처
3. **실증 평가** — 실제 기술문서 개정 이력을 활용한 정확도/성능 벤치마크

---

## 3. 연구 방법론

### 3.1 시스템 아키텍처 (3단계 파이프라인)

```
[1단계] 텍스트 diff (jsdiff, 클라이언트, 즉시)
    ↓ 변경 구간 추출
[2단계] 구간 정렬 + 컨텍스트 수집 (빠름, 로컬)
    ↓ {원문, 수정문, 전후 맥락}
[3단계] LLM 의미 분류 (Ollama, 로컬, 온디맨드)
    ↓ {분류 태그, 신뢰도, 설명}
```

> 레퍼런스: fda-guidance-diff (FDA 규제문서 비교, Gemini Flash, 정확도 90~100%)

### 3.2 변경 유형 분류 체계

| 태그 | 의미 | 검토 우선순위 |
|------|------|-------------|
| EDITORIAL | 편집상 변경 (오타, 서식, 용어 통일) | 낮음 |
| CLARIFICATION | 표현 명확화, 의미 동일 | 낮음 |
| STRICTER | 요구사항/기준 강화 | 높음 |
| MORE_LENIENT | 요구사항/기준 완화 | 높음 |
| EXPANDED | 범위/내용 확대 | 중간 |
| RESTRUCTURED | 구조 재배치, 의미 동일 | 낮음 |
| NUMERIC | 수치/단위 변경 | 높음 |

### 3.3 실험 설계

#### 독립변수
- 분류 방식: (A) 규칙 기반, (B) LLM 단독, (C) 하이브리드(규칙+LLM)
- LLM 모델: Ollama에서 구동 가능한 모델 (예: llama3, gemma2, qwen2.5 등)

#### 종속변수
- 분류 정확도 (Precision, Recall, F1)
- 처리 시간 (구간당 평균 응답 시간)
- 검토자 효율성 (선택적: 사용자 스터디)

#### 데이터셋
- 실제 항공/방산 기술문서 개정 이력 (SWA, SRS, SDD 등)
- 변경 구간별 전문가 라벨링 (Gold Standard)
- 최소 200~500 변경 구간

#### 베이스라인
- fda-guidance-diff (Gemini Flash, 영문 규제문서) 결과와 방법론 비교
- 규칙 기반 분류 (키워드 매칭, 수치 패턴 감지)

### 3.4 평가 지표

| 지표 | 설명 |
|------|------|
| Macro F1 | 7개 분류 태그의 평균 F1 (클래스 불균형 대응) |
| 처리 시간 | 구간당 평균 분류 소요 시간 (ms) |
| 검토 시간 절감율 | (선택) 의미 분류 유무에 따른 검토 시간 차이 |
| Cohen's Kappa | 전문가 간 라벨링 일치도 (데이터셋 품질 검증) |

---

## 4. 실현 가능성 분석

### 4.1 직장인 파트타임 적합성

| 항목 | 평가 |
|------|------|
| 구현 부담 | **낮음** — 이미 동작하는 플랫폼(Phase 1~5) 위에 API 1개 + 프론트 버튼 추가 수준 |
| 데이터 접근 | **양호** — 현업에서 기술문서 개정 이력 확보 가능 (민감 정보 제거 후 활용) |
| 실험 환경 | **용이** — Ollama 로컬 설치, 별도 GPU 서버 불필요 (CPU 추론 가능) |
| 논문 작성 | **집중 가능** — 시스템 구현보다 실험/평가/분석에 시간 투자 |
| 소요 기간 | 3~6개월 (구현 1개월, 라벨링 1~2개월, 실험/논문 1~2개월) |

### 4.2 리스크

| 리스크 | 대응 |
|--------|------|
| 한국어 LLM 분류 정확도 부족 | 프롬프트 엔지니어링 + few-shot 예시로 개선. 여러 모델 비교 실험 자체가 기여 |
| 데이터셋 규모 부족 | 200구간 이상이면 학회 논문 수준 충분. KCI 저널은 300~500 권장 |
| 민감 정보 문제 | 문서 내용을 일반화하거나, 공개 기술문서(KS 표준, 공공 SRS 등) 활용 |

---

## 5. 투고 대상

### 5.1 국내 학술대회 (먼저 발표 → 확장판 저널)

| 학회 | 시기 | 비고 |
|------|------|------|
| 한국정보과학회 KCC | 매년 6월 | 단기 논문(4p) 발표 후 확장 가능 |
| 한국소프트웨어공학학회 KCSE | 매년 2월 | SW 공학 특화, 도구 논문 적합 |
| 한국정보처리학회 ASK | 매년 5월/11월 | NLP/AI 응용 트랙 |

### 5.2 KCI 저널

| 저널 | 분야 | 비고 |
|------|------|------|
| 정보처리학회논문지 (소프트웨어 및 데이터공학) | SW 공학 + NLP | 가장 적합 |
| 한국정보과학회 컴퓨팅의 실제 논문지 | 시스템/도구 | 실용 시스템 논문 환영 |
| 한국콘텐츠학회논문지 | 융합 | 학제간 연구 수용적 |

### 5.3 국제 (선택적)

| 학회/저널 | 비고 |
|----------|------|
| APSEC (Asia-Pacific Software Engineering Conference) | 아시아 SW 공학, CJK 연구 수용적 |
| SANER (Software Analysis, Evolution, and Reengineering) | 문서 진화 관련 |
| LREC-COLING | 언어 자원 + NLP, 한국어 특화 연구 환영 |

---

## 6. 유사 시스템 조사 요약

### 6.1 상용 제품

| 제품 | 접근 방식 | 속도 | 시장 위치 |
|------|----------|------|----------|
| Draftable | 전통 diff 전용 (AI 없음) | 수 초 | 900+ 법률사 |
| Litera Compare + Lito | 전통 diff + AI 에이전트(요약/위험분석) | diff 즉시, AI 별도 | 법률 업계 72% 점유 |
| Diffchecker Pro | 텍스트 diff + "AI로 요약" 버튼 | diff 즉시, AI 수 초 | 일반 사용자 |
| BlackBoiler | Word Track Changes + AI 마크업 | NDA 2분 | 계약 자동화, 검토 70% 단축 |
| Spellbook | GPT-5/Claude 기반 계약 분석 | 실시간 Word 애드인 | 4000+ 법률팀, 80+ 국가 |
| Luminance | 멀티모델 AI, 1000+ 조항 자동 식별 | 40% 시간 절감 | 기업 법무 |
| Robin AI | Anthropic Claude + AWS | - | 50만+ 문서 |

### 6.2 오픈소스/연구 프로젝트

| 프로젝트 | 접근 방식 | 핵심 특징 |
|----------|----------|----------|
| [fda-guidance-diff](https://github.com/tanayvenkata/fda-guidance-diff) ★ | 추출→BM25→Gemini Flash 분류 | FDA 규제문서, 8종 분류 태그, 정확도 90~100% |
| [SemanticDiff](https://github.com/Labic-ICMC-USP/SemanticDiff) | reflow 내성 PDF diff + LLM 검증 | 학술/기술 논문, PDF 스트림 직접 하이라이트 |
| [redline-summarizer](https://github.com/noamrazbuilds/redline-summarizer) | Claude API 계약 비교 | 교통신호 위험등급, 조항 유형 분류 |
| [lexi-flow](https://github.com/bhagwat-chate/lexi-flow) | RAG 기반 문서 비교 | 멀티 LLM (GPT-4o/Gemini/DeepSeek) |
| [DVCS](https://github.com/SaintFreddy/dvcs) | 문서 버전 관리, 의미 단위 diff | Office 파일 구조 분해(CDM), 3-way merge |

### 6.3 시장 인사이트

- **업계 표준 아키텍처**: 빠른 diff 즉시 표시 → AI 분류는 비동기 오버레이
- **전체 문서를 LLM에 보내는 제품은 없음** — diff 결과(변경 구간)만 LLM에 전달
- **"AI 피로감"**: 사용자는 AI 기능 자체보다 측정 가능한 시간 절감을 원함 (Draftable CEO)
- **CJK 특화 도구 부재**: 한국어 기술문서 의미비교는 시장 공백 → 연구 기여 포인트

---

## 7. 참고 문헌 (추후 정리)

- fda-guidance-diff: https://github.com/tanayvenkata/fda-guidance-diff
- SemanticDiff: https://github.com/Labic-ICMC-USP/SemanticDiff
- redline-summarizer: https://github.com/noamrazbuilds/redline-summarizer
- jsdiff: https://github.com/kpdecker/jsdiff
- h2o.ai LLM-Powered Document Comparison: https://h2o.ai/LLM-Powered-Document-Comparison/
- Draftable Lawtech Summit 보도 (AI 피로감 관련)
- Litera Compare + Lito 제품 문서

---

## 8. 다음 단계

1. [ ] 지도교수 상담 — 주제 적합성 및 방향 확인
2. [ ] 데이터셋 확보 계획 수립 — 사용 가능한 기술문서 개정 이력 목록화
3. [ ] Phase 6-1 구현 — Compare 시스템에 AI 분류 API 추가
4. [ ] 파일럿 실험 — 소규모(50구간) 분류 정확도 확인
5. [ ] 본 실험 — 200~500구간 라벨링 + 모델 비교
6. [ ] 논문 초고 작성
