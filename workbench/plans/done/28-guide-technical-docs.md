# Plan-28: 플랫폼 가이드 확장 — 기술 문서 추가 및 권한별 메뉴 노출

> **작성일**: 2026-04-06
> **상태**: 완료
> **목적**: 기술/보고 성격의 문서 4건을 플랫폼 가이드에 추가하고, 권한별 메뉴 노출 기능을 도입한다

---

## 1. 배경

### 1.1 현황

플랫폼 가이드에 사용법 문서 5건이 등록되어 있다:

| 문서 | 성격 |
|------|------|
| 플랫폼 소개 | 기능 중심 개요 |
| Explorer 사용법 | 사용자 How-to |
| Notebook 사용법 | 사용자 How-to |
| Verify 사용법 | 사용자 How-to |
| 관리자 가이드 | 관리자 How-to |

모두 **"어떻게 쓰는가"** 관점이다. **"어떻게 만들어졌는가", "왜 이렇게 만들었는가"** 를 다루는 기술/보고 문서는 `docs/` 디렉토리에 마크다운으로만 존재하며, 플랫폼 콘텐츠로 활용되지 않고 있다.

### 1.2 목표

1. `docs/` 소스 자료를 가공하여 기술 문서 4건을 플랫폼 가이드에 추가
2. 가이드 메뉴를 "사용 가이드" / "기술 문서" 하위 그룹으로 재구성
3. "기술 문서" 그룹은 admin 권한에만 노출 (메뉴 필터링)
4. 가이드 문서는 검색/RAG 인덱싱 대상에서 제외 유지

### 1.3 기대 효과

- **Dog-fooding**: 플랫폼이 자기 문서를 서빙 → 실용성 직접 증명
- **데모 콘텐츠 확보**: 발표/보고 시 PPT 대신 플랫폼에서 직접 공유
- **콘텐츠 충실화**: 의미 있는 실제 문서로 플랫폼의 가치 체감

---

## 2. 설계

### 2.1 메뉴 구조

```
플랫폼 가이드/
├── 사용 가이드/                    ← 전체 공개 (role 제한 없음)
│   ├── 플랫폼 소개                 (기존)
│   ├── Explorer 사용법             (기존)
│   ├── Notebook 사용법             (기존)
│   ├── Verify 사용법               (기존)
│   └── 관리자 가이드               (기존)
└── 기술 문서/                      ← admin 전용 (role: "admin")
    ├── 시스템 아키텍처             (신규)
    ├── RAG 검색 기술 보고서        (신규)
    ├── 개발 경과 보고              (신규)
    └── 문서 검증 규칙 레퍼런스     (신규)
```

### 2.2 menu.json 변경

```json
{
  "label": "플랫폼 가이드",
  "icon": "info",
  "children": [
    {
      "label": "사용 가이드",
      "children": [
        { "label": "플랫폼 소개", "url": "contents/guide/platform-overview.html" },
        { "label": "Explorer 사용법", "url": "contents/guide/explorer-guide.html" },
        { "label": "Notebook 사용법", "url": "contents/guide/notebook-guide.html" },
        { "label": "Verify 사용법", "url": "contents/guide/verify-guide.html" },
        { "label": "관리자 가이드", "url": "contents/guide/admin-guide.html" }
      ]
    },
    {
      "label": "기술 문서",
      "role": "admin",
      "children": [
        { "label": "시스템 아키텍처", "url": "contents/guide/architecture.html" },
        { "label": "RAG 검색 기술 보고서", "url": "contents/guide/rag-report.html" },
        { "label": "개발 경과 보고", "url": "contents/guide/dev-progress.html" },
        { "label": "문서 검증 규칙 레퍼런스", "url": "contents/guide/verify-rules-ref.html" }
      ]
    }
  ]
}
```

### 2.3 권한별 메뉴 필터링

**방식**: `role` 필드 기반 프론트엔드 필터링

- 메뉴 노드에 `"role": "admin"` 또는 `"role": "editor"` 추가 가능
- `role` 필드가 없으면 전체 공개 (하위 호환)
- 프론트엔드 메뉴 렌더링 시 현재 사용자 역할과 비교하여 미달 시 노드 제거
- 역할 계층: `viewer(1) < editor(2) < admin(3)` — 상위 역할은 하위 포함

**필터링 위치**: 프론트엔드 메뉴 렌더링 함수 (트리 순회 시 `role` 체크)

```
// 의사 코드
function filterMenuByRole(nodes, userRole) {
  return nodes.filter(node => {
    if (node.role && ROLE_LEVEL[userRole] < ROLE_LEVEL[node.role]) return false
    if (node.children) node.children = filterMenuByRole(node.children, userRole)
    return true
  })
}
```

**백엔드 보호**: 가이드 HTML 파일은 정적 서빙이므로 URL 직접 접근은 차단하지 않는다.
기밀 문서가 아닌 기술 참고 문서이므로, 메뉴 비노출만으로 충분하다.

### 2.4 검색/RAG 인덱싱 제외

현재 가이드 문서는 `search-index.json`과 `vector-index/`에 포함되지 않는다.
신규 문서도 동일하게 인덱싱 대상에서 제외한다.

- `contents/guide/` 경로의 HTML은 인덱싱 스크립트에서 제외 (현재 동작 유지)
- 검색/RAG에서 가이드 내용이 노출되지 않음 → 권한 우회 불가

---

## 3. 신규 문서 상세

### 3.1 시스템 아키텍처 (`architecture.html`)

| 항목 | 내용 |
|------|------|
| 대상 독자 | 개발자, 기술 관리자, 운영자 |
| 주요 소스 | `docs/05-ARCHITECTURE.md`, `docs/03-BACKEND-SETUP.md`, `docs/10-PRODUCTION-READINESS.md` |
| 구성 | 3-tier 구조도 (Tomcat + FastAPI + Ollama), 서비스 컴포넌트 맵, API 설계 패턴, 폐쇄망 제약 하의 기술 선택 근거, 폴더 구조, 배포 토폴로지 |
| 기존과 차별 | "플랫폼 소개"는 기능 중심 개요. 이 문서는 내부 구조와 기술적 의사결정을 다룸 |

### 3.2 RAG 검색 기술 보고서 (`rag-report.html`)

| 항목 | 내용 |
|------|------|
| 대상 독자 | AI/검색 엔지니어, 기술 관리자 |
| 주요 소스 | `docs/RAG-TECHNICAL-REPORT.md`, `docs/06-RAG-PIPELINE.md` |
| 구성 | 4단계 진화 (키워드 → 하이브리드 → 리랭킹 → 에이전틱), 구조 보존 인덱싱, 하이브리드 검색 (RRF 30:70), 평가 지표 (Recall@5 100%, MRR 0.967), 멀티턴 대화, 한계와 향후 과제 |
| 기존과 차별 | "Explorer 사용법"은 검색 쓰는 법. 이 문서는 검색이 왜 잘 되는지 기술적 근거 제시 |

### 3.3 개발 경과 보고 (`dev-progress.html`)

| 항목 | 내용 |
|------|------|
| 대상 독자 | 경영진, 이해관계자, 프로젝트 관리자 |
| 주요 소스 | `docs/platform_report_slides.md`, `docs/webbook_report_slides.md`, `docs/09-PLATFORM-VISION.md` |
| 구성 | 7단계 진화 타임라인 (정적 웹북 → 지식 플랫폼), 4대 서브시스템 개발 현황, 주요 성과 수치, 기술 스택 선택 배경, 확장 전략과 로드맵 |
| 기존과 차별 | "플랫폼 소개"는 현재 기능 나열. 이 문서는 어디서 출발해서 어디까지 왔고 어디로 가는가의 서사 |

### 3.4 문서 검증 규칙 레퍼런스 (`verify-rules-ref.html`)

| 항목 | 내용 |
|------|------|
| 대상 독자 | 기술문서 작성자, 품질 담당자, 규격 관리자 |
| 주요 소스 | `docs/12-VERIFY-SYSTEM.md`, `docs/11-COMPARE-SYSTEM.md` |
| 구성 | 3대 표준 (ASD-STE100, MIL-STD-961E, MIL-STD-38784B) 개요, 21종 규칙 상세 (판정 기준, 예시, 적용 범위), 유사도 검사 알고리즘, 점수 체계 |
| 기존과 차별 | "Verify 사용법"은 화면 조작법. 이 문서는 각 규칙이 무엇을 검사하는지 실무 레퍼런스 |

---

## 4. 구현 계획

### Phase 1: 권한별 메뉴 필터링 (선행)

| 단계 | 작업 | 파일 |
|------|------|------|
| 1-1 | 프론트엔드 메뉴 렌더링에 `role` 필터링 추가 | `js/app.js` (메뉴 렌더 함수) |
| 1-2 | menu.json에 하위 그룹 구조 적용 | `data/menu.json` |
| 1-3 | 시스템 보호 로직에 하위 그룹 반영 | `backend/api/menu.py` |
| 1-4 | 동작 검증 — viewer/editor 계정으로 "기술 문서" 미노출 확인 | 수동 테스트 |

### Phase 2: 문서 작성

| 단계 | 작업 | 산출물 |
|------|------|--------|
| 2-1 | 시스템 아키텍처 | `contents/guide/architecture.html` |
| 2-2 | RAG 검색 기술 보고서 | `contents/guide/rag-report.html` |
| 2-3 | 개발 경과 보고 | `contents/guide/dev-progress.html` |
| 2-4 | 문서 검증 규칙 레퍼런스 | `contents/guide/verify-rules-ref.html` |

모든 문서는 `GUIDE-STYLE.md` 규칙 준수:
- `po-*` CSS 클래스 사용
- 이모지 금지, 담백한 톤
- 1컬럼 우선, 테이블 4열 이하
- 스크린샷 포함 시 `contents/guide/images/`에 저장

### Phase 3: 검증

| 단계 | 작업 |
|------|------|
| 3-1 | admin 계정: 9건 모두 메뉴 노출 및 문서 열람 확인 |
| 3-2 | viewer/editor 계정: "기술 문서" 그룹 미노출 확인 |
| 3-3 | 검색/RAG에서 가이드 문서 미검색 확인 |
| 3-4 | 관리자 메뉴 편집 시 시스템 보호 정상 동작 확인 |

---

## 5. 영향 범위

| 영역 | 변경 | 리스크 |
|------|------|--------|
| `data/menu.json` | 하위 그룹 구조 변경 | 메뉴 렌더링 호환성 확인 필요 |
| `js/app.js` | 메뉴 필터링 로직 추가 | 기존 메뉴 동작에 영향 없도록 `role` 미지정 = 전체 공개 |
| `backend/api/menu.py` | 시스템 보호 대상 확장 | 기존 보호 로직과 충돌 없음 |
| `contents/guide/` | HTML 4건 추가 | 인덱싱 제외 현행 유지 |
| 검색/RAG | 변경 없음 | — |

---

## 6. 하지 않는 것

- **백엔드 URL 접근 제어**: 기밀 문서가 아니므로 메뉴 비노출로 충분
- **권한별 검색 인덱스 분리**: 가이드 문서 자체가 인덱싱 대상이 아님
- **docs/ 마크다운 전부 등록**: 선별된 4건만 가공하여 등록
- **기존 5건 문서 수정**: 구조 변경(하위 그룹 이동)만, 내용은 그대로
