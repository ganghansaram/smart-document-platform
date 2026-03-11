# 챗봇 피드백 루프 및 프롬프트 설정화 계획서

> **문서 번호**: Plan-11
> **작성일**: 2026-03-11
> **상태**: ✅ 구현 완료
> **선행**: Plan-10 Phase 1~3 완료
> **대상 시스템**: Explorer RAG 챗봇 + 관리자 설정

---

## 1. 목표

Plan-10(Phase 1~3)에서 구축한 질문 라우터, Agentic RAG, 신뢰도 표시가 **실제로 답변 품질을 개선하는지** 확인하고, **관리자가 데이터 기반으로 조정**할 수 있는 피드백 루프를 완성한다.

```
피드백 수집 → 통계 대시보드 → 관리자 패턴 파악 → 설정 조정 → 품질 변화 확인
   Step 1         Step 3            사람           Step 2         Step 3
```

---

## 2. 현황 분석 및 식별된 이슈

### 2-1. 시스템 프롬프트 이중 구조 (⚠ 주의)

현재 시스템 프롬프트가 **두 곳에** 존재한다:

| 위치 | 용도 | 설정 가능 여부 |
|------|------|:---:|
| `backend/services/llm_client.py:17-39` (`SYSTEM_PROMPT`) | 백엔드 RAG 파이프라인 | ❌ 하드코딩 |
| `settings_service.py` → `frontend.ai_system_prompt` | 프론트엔드 직접 Ollama 호출 모드 | ✅ 관리자 UI |

**문제**: 백엔드 모드(기본값)에서는 `llm_client.py`의 하드코딩 프롬프트를 사용하므로, 관리자 UI에서 프롬프트를 바꿔도 반영되지 않는다. 관리자 UI의 `ai_system_prompt` 필드 설명에 "백엔드 RAG 사용 시 서버 설정이 우선 적용됨"이라고 적혀 있지만, 실제로는 서버 측 설정 항목 자체가 없다.

**해결**: `config.py`에 `CHAT_SYSTEM_PROMPT`를 추가하고, `llm_client.py`가 이를 참조하도록 변경.

### 2-2. 스트리밍 done 페이로드에 route 누락

`chat.py`의 `_routed_search()`는 `route` 필드(SIMPLE/COMPARE/REASON/CHAT)를 반환하지만, 스트리밍 `done` 페이로드에는 포함되지 않고 있다. 피드백 저장 시 어떤 경로로 처리됐는지 기록하려면 이 필드가 필요하다.

```python
# 현재 done_payload (chat.py:394-405)
done_payload = {
    "type": "done",
    "sources": [...],
    "model": model_name,
    "conversation_id": session.id,
    "confidence": rag_meta["confidence"],
    "reasoning_steps": rag_meta["reasoning_steps"],
    "search_queries": rag_meta["search_queries"],
    # route 없음 ← 추가 필요
}
```

### 2-3. 메시지 식별자 부재

현재 `AIChatState.messages`는 `{ role, content }`만 저장한다. 피드백을 특정 답변에 연결하려면 메시지별 고유 ID가 필요하다.

### 2-4. analytics.db 스키마 확장

현재 `events` 테이블 하나로 방문/검색/채팅 이벤트를 저장한다. 피드백은 메타데이터가 풍부하므로 별도 `chat_feedback` 테이블이 적절하다.

### 2-5. 관리자 대시보드 구조

`js/analytics.js`의 `renderAnalyticsDashboard()`가 대시보드 패널을 렌더링한다. 기존 섹션(방문자, 인기 페이지, 인기 검색어, 채팅 통계) 하단에 피드백 섹션을 추가하는 구조.

---

## 3. 구현 단계

### Step 1: 피드백 수집 (프론트엔드 + 백엔드 API)

#### 1-A. 스트리밍 done 페이로드에 route 추가

- **파일**: `backend/api/chat.py`
- **변경**: done_payload에 `"route": rag_meta["route"]` 추가
- **영향**: 프론트엔드에서 추가 필드만 읽으면 됨. 기존 필드 불변
- **위험도**: 없음

#### 1-B. 피드백 API 엔드포인트

- **파일**: `backend/api/chat.py` (기존 파일에 추가)
- **엔드포인트**: `POST /api/chat/feedback`
- **요청 본문**:
  ```json
  {
    "conversation_id": "abc123",
    "question": "KF-21의 엔진 추력은?",
    "answer_preview": "KF-21의 엔진 추력 정보는...",
    "feedback": "positive",
    "route": "SIMPLE",
    "confidence": "high",
    "model": "gemma3:4b",
    "sources_count": 5
  }
  ```
- **응답**: `{ "success": true }`
- **인증**: 로그인 사용자 (username 자동 추출)

#### 1-C. analytics.db에 chat_feedback 테이블

- **파일**: `backend/services/analytics.py`
- **스키마**:
  ```sql
  CREATE TABLE IF NOT EXISTS chat_feedback (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      timestamp TEXT DEFAULT (datetime('now', 'localtime')),
      username TEXT,
      conversation_id TEXT,
      question TEXT,
      answer_preview TEXT,
      feedback TEXT NOT NULL,       -- 'positive' | 'negative'
      route TEXT,                   -- 'SIMPLE' | 'COMPARE' | 'REASON' | 'CHAT'
      confidence TEXT,              -- 'high' | 'medium' | 'low'
      model TEXT,
      sources_count INTEGER DEFAULT 0
  );
  ```
- **answer_preview**: 전체 답변이 아닌 앞 200자만 저장 (DB 크기 관리)
- **영향**: 기존 `events` 테이블 불변. 별도 테이블이므로 기존 쿼리에 영향 없음

#### 1-D. 챗봇 UI에 피드백 버튼

- **파일**: `js/ai-chat.js`, `css/ai-chat.css`
- **위치**: `finalizeStreamingMessage()` 내부, 소스 표시 아래에 추가
- **DOM 구조**:
  ```html
  <div class="ai-chat-message assistant">
    <span class="message-content">답변 내용...</span>
    <div class="ai-chat-confidence">⚠ ...</div>        <!-- 기존 (조건부) -->
    <div class="ai-chat-sources">참고: ...</div>         <!-- 기존 (조건부) -->
    <div class="ai-chat-feedback">                       <!-- 신규 -->
      <button class="feedback-btn positive" title="도움이 됐어요">👍</button>
      <button class="feedback-btn negative" title="아쉬워요">👎</button>
    </div>
  </div>
  ```
- **동작**:
  - 클릭 시 `/api/chat/feedback` 호출
  - 호출 후 클릭된 버튼 활성화 상태로 변경, 양쪽 버튼 비활성화 (중복 방지)
  - 메타데이터(question, route, confidence, model, sources_count)는 `done` 이벤트에서 캡처하여 메시지 요소의 `dataset`에 저장
- **주의사항**:
  - `requestViaBackendStream()`에서 `done` 이벤트의 `route`, `model` 등을 캡처해야 함
  - 직접 Ollama 모드(`useBackend=false`)에서는 피드백 버튼 미표시 (API가 없으므로)
  - CHAT 라우팅(인사/잡담)에서는 피드백 버튼 미표시 (분석 가치 없음)

#### 1-D 영향 분석

| 기존 함수 | 변경 내용 | 영향 |
|-----------|----------|------|
| `finalizeStreamingMessage()` | 세 번째 파라미터를 메타데이터 객체로 확장 | 시그니처 변경. 호출부 1곳 수정 (line 594) |
| `requestViaBackendStream()` | done 이벤트에서 route, model 캡처 | 변수 추가만, 기존 로직 불변 |
| `createStreamingMessage()` | 변경 없음 | - |
| `updateStreamingMessage()` | 변경 없음 | - |
| `addMessage()` (비스트리밍) | 피드백 버튼 미추가 (직접 Ollama 모드) | 변경 없음 |

> **호출부 정확한 목록** (검증 완료):
> - `finalizeStreamingMessage()` 호출: `requestViaBackendStream()` 내부 1곳 (line 594)
>   - `executeQuickAction()`은 `requestViaBackendStream()`을 호출하므로 간접 경유 (별도 수정 불필요)
> - `addMessage()` 호출: `sendMessage()` 3곳, `executeQuickAction()` 3곳 — 비스트리밍 경로이므로 변경 없음
>
> **`addMessage()` vs `finalizeStreamingMessage()` 역할 구분**:
> - `addMessage(role, content, sources)` — 비스트리밍 메시지 (직접 Ollama 모드, 에러). 소스를 직접 렌더링. 피드백 버튼 대상 아님
> - `finalizeStreamingMessage(messageEl, sources, meta)` — 스트리밍 완료 후 마무리 (백엔드 RAG 모드). 피드백 버튼 추가 대상

---

### Step 2: 시스템 프롬프트 설정화 (5-B)

#### 2-A. config.py에 CHAT_SYSTEM_PROMPT 추가

- **파일**: `backend/config.py`
- **변경**: 현재 `llm_client.py`에 하드코딩된 `SYSTEM_PROMPT` 문자열을 `config.CHAT_SYSTEM_PROMPT`로 이동
- **기본값**: 현재 프롬프트 그대로 (KF-21 전문 어시스턴트)

#### 2-B. llm_client.py에서 config 참조

- **파일**: `backend/services/llm_client.py`
- **변경**:
  ```python
  # Before
  SYSTEM_PROMPT = """당신은 KF-21 전투기..."""

  # After
  def _get_system_prompt():
      return getattr(config, 'CHAT_SYSTEM_PROMPT', '') or DEFAULT_SYSTEM_PROMPT

  DEFAULT_SYSTEM_PROMPT = """당신은 KF-21 전투기..."""
  ```
- **안전장치**: config 값이 비어있으면 기본 프롬프트 사용 (실수로 빈값 저장 시 보호)
- **영향**: `_build_prompt()`와 `generate_response_stream()`에서 `SYSTEM_PROMPT` 대신 `_get_system_prompt()` 호출. 동작 변경 없음 (같은 값 반환)

#### 2-C. settings_service.py 매핑

- **파일**: `backend/services/settings_service.py`
- **변경**:
  - `DEFAULT_SETTINGS["ai"]`에 `"chat_system_prompt": "(기본 프롬프트 전문)"` 추가
  - `apply_to_config()`에 `_set(ai, "chat_system_prompt", "CHAT_SYSTEM_PROMPT", ...)` 추가
  - `_NO_RESTART`에 `"ai.chat_system_prompt"` 추가 (즉시 반영)

#### 2-D. 관리자 UI에 프롬프트 편집 필드

- **파일**: `js/admin-settings.js`
- **위치**: Explorer → AI/RAG 탭, "리랭커 / 쿼리 재작성" 섹션 다음에 새 섹션 추가
- **필드**:
  ```javascript
  {
      title: '챗봇 프롬프트',
      fields: [
          {
              group: 'ai', key: 'chat_system_prompt',
              label: '시스템 프롬프트 (백엔드 RAG)',
              type: 'textarea', rows: 12, restart: false,
              desc: '챗봇이 답변 생성 시 따르는 지침. 도메인, 답변 형식, 언어 등을 지정합니다.'
          }
      ]
  }
  ```
- **기존 `frontend.ai_system_prompt` 필드**: 유지 (직접 Ollama 모드용). 설명을 "백엔드 미사용(직접 모드) 시에만 적용됩니다"로 명확화

#### 2-D 영향 분석

기존 관리자 UI 탭 구조 (`tab-ai`) 내에 섹션을 추가하는 것이므로:
- 탭 전환 로직 변경 없음
- 저장/적용 로직 변경 없음 (기존 `_collectSettings()` → `_set()` 흐름 그대로)
- textarea 렌더링은 기존 `renderControl()` (line 615)에서 지원됨

---

### Step 3: 피드백 대시보드

#### 3-A. 피드백 통계 쿼리 함수

- **파일**: `backend/services/analytics.py`
- **추가 함수**:
  ```python
  def get_feedback_summary(days=30):
      """라우팅별/신뢰도별 만족도 통계"""
      # Returns:
      # {
      #   "total": { "positive": 18, "negative": 7, "rate": 72 },
      #   "by_route": {
      #     "SIMPLE":  { "positive": 10, "negative": 2, "rate": 83 },
      #     "COMPARE": { "positive": 3,  "negative": 2, "rate": 60 },
      #     "REASON":  { "positive": 4,  "negative": 3, "rate": 57 },
      #     "CHAT":    { "positive": 1,  "negative": 0, "rate": 100 },
      #   },
      #   "by_confidence": {
      #     "high":   { "positive": 15, "negative": 3, "rate": 83 },
      #     "medium": { "positive": 2,  "negative": 3, "rate": 40 },
      #     "low":    { "positive": 1,  "negative": 1, "rate": 50 },
      #   }
      # }

  def get_recent_negative(limit=20):
      """최근 부정 피드백 질문 목록"""
      # Returns: [
      #   { "timestamp": "...", "question": "...", "route": "REASON",
      #     "confidence": "medium", "model": "gemma3:4b", "answer_preview": "..." },
      #   ...
      # ]

  def get_daily_feedback(days=14):
      """일별 피드백 추세"""
      # Returns: [{ "day": "2026-03-10", "positive": 5, "negative": 2 }, ...]
  ```

#### 3-B. 대시보드 API 확장

- **파일**: `backend/api/analytics.py`
- **변경**: 기존 `GET /api/analytics/dashboard` 응답에 `feedback` 필드 추가
  ```python
  # 기존 응답에 병합
  return {
      ...기존 필드(visitors, pages, searches, chat)...,
      "feedback": {
          "summary": get_feedback_summary(),
          "recent_negative": get_recent_negative(10),
          "daily": get_daily_feedback(14),
      }
  }
  ```
- **영향**: 기존 필드 불변, 새 필드 추가만. 프론트엔드가 해당 필드를 읽지 않으면 무시됨

#### 3-C. 대시보드 UI 렌더링

- **파일**: `js/analytics.js`
- **위치**: `renderAnalyticsDashboard()` 함수 하단, 기존 "채팅 통계" 섹션 아래에 추가
- **UI 구성**:

  **① 만족도 요약 카드**: 전체 👍 비율 (큰 숫자 + 프로그레스 바)

  **② 라우팅별 만족도 테이블**:
  ```
  | 경로      | 👍    | 👎    | 만족도  |
  |-----------|-------|-------|---------|
  | SIMPLE    | 10    | 2     | 83%     |
  | COMPARE   | 3     | 2     | 60%     |
  | REASON    | 4     | 3     | 57%     |
  ```

  **③ 최근 부정 피드백 목록** (최대 10건):
  ```
  ┌──────────────────────────────────────────┐
  │ 2026-03-11 14:30                         │
  │ Q: "FY14~20 예산 추세 분석해줘"           │
  │ 경로: REASON / 신뢰도: medium             │
  │ A: "FY 2014년부터 2020년까지의 국방..."    │
  └──────────────────────────────────────────┘
  ```

  **④ 일별 피드백 추세 차트**: 기존 방문자 차트와 동일한 바 차트 패턴 재사용. 긍정(초록)/부정(빨강) 스택

- **CSS**: 기존 `admin-settings.css`의 대시보드 스타일(`.admin-chart-*`, `.admin-stat-*`) 재사용. 추가 필요한 건 피드백 카드 스타일 소량

#### 3-C 영향 분석

`renderAnalyticsDashboard()`는 독립 함수로, 대시보드 패널 컨테이너에 innerHTML을 빌드한다. 기존 섹션 코드를 건드리지 않고 하단에 HTML을 append하는 구조이므로 기존 대시보드 기능에 영향 없음.

---

## 4. 파일 변경 요약

| 파일 | 변경 유형 | 내용 |
|------|:---------:|------|
| `backend/config.py` | 수정 | `CHAT_SYSTEM_PROMPT` 추가 |
| `backend/services/llm_client.py` | 수정 | 하드코딩 `SYSTEM_PROMPT` → `config.CHAT_SYSTEM_PROMPT` 참조 |
| `backend/services/settings_service.py` | 수정 | `chat_system_prompt` 매핑 추가 |
| `backend/services/analytics.py` | 수정 | `chat_feedback` 테이블 + 통계 쿼리 함수 3개 |
| `backend/api/chat.py` | 수정 | done 페이로드에 `route` 추가, `POST /api/chat/feedback` 엔드포인트 |
| `backend/api/analytics.py` | 수정 | dashboard 응답에 feedback 섹션 추가 |
| `js/ai-chat.js` | 수정 | 피드백 버튼 렌더링 + API 호출 |
| `js/admin-settings.js` | 수정 | AI/RAG 탭에 프롬프트 편집 섹션 추가 |
| `js/analytics.js` | 수정 | 대시보드에 피드백 통계 섹션 추가 |
| `css/ai-chat.css` | 수정 | 피드백 버튼 스타일 |

**신규 파일**: 없음 (모두 기존 파일 수정)

---

## 5. 위험 요소 및 대응

| 위험 | 영향 | 대응 |
|------|------|------|
| `llm_client.py` SYSTEM_PROMPT 변경 시 기존 답변 품질 저하 | 프롬프트가 비어있으면 답변 형식 붕괴 | `_get_system_prompt()`에서 빈값 시 기본 프롬프트 폴백 |
| `finalizeStreamingMessage()` 시그니처 변경 | 호출부 수정 누락 | 호출부는 `requestViaBackendStream()` 내부 line 594 **1곳만**. `executeQuickAction()`은 `requestViaBackendStream()`을 호출하므로 별도 수정 불필요 |
| 대시보드 API 응답 크기 증가 | 피드백 데이터가 많으면 응답 느려짐 | `recent_negative` limit=10, `daily` days=14로 제한 |
| 프론트엔드 직접 모드에서 피드백 버튼 오작동 | API 없이 피드백 전송 시도 시 에러 | `useBackend` 체크하여 직접 모드에서는 버튼 미표시 |
| done 이벤트 전에 사용자가 채팅창 닫음 | 메타데이터 캡처 실패 → 피드백 데이터 불완전 | done 미수신 시 피드백 버튼 미표시 (정상 완료 메시지만 대상) |
| CHAT 라우팅 답변에 피드백 | 인사/잡담 피드백은 분석 가치 없음 | CHAT 라우팅 시 피드백 버튼 미표시 |
| analytics.db 테이블 추가 시 기존 데이터 영향 | 기존 events 테이블 손상 가능성 | `CREATE TABLE IF NOT EXISTS` 사용. 별도 테이블이므로 기존 스키마 불변. `_init_db()`의 `executescript()` 내에 추가 |
| `_build_prompt()`에서 system 파라미터 전달 경로 | `generate_response()`와 `generate_response_stream()` 양쪽에서 사용 | 두 함수 모두 `system=SYSTEM_PROMPT` → `system=_get_system_prompt()`로 변경. 호출 위치: line 117 (`generate`), line 148 (`generate_stream`) |

---

## 6. 실행 순서

```
Step 2-A,B,C (프롬프트 설정화, 백엔드)     ← 독립 작업, 먼저
    ↓
Step 2-D (프롬프트 관리자 UI 필드)          ← 2-A~C 완료 후
    ↓
Step 1-A (done 페이로드 route 추가)         ← 선행 필요
    ↓
Step 1-B,C (피드백 API + DB)               ← 독립 작업
    ↓
Step 1-D (챗봇 피드백 버튼)                 ← 1-A~C 완료 후
    ↓
Step 3-A,B (피드백 통계 쿼리 + API)         ← 1-B,C 완료 후
    ↓
Step 3-C (대시보드 UI)                      ← 3-A,B 완료 후
```

---

## 7. 검증 계획

### 프롬프트 설정화 검증
- 관리자 설정 → AI/RAG → 프롬프트 편집 → 저장
- 챗봇에서 질문 → 변경된 프롬프트 반영 확인
- 프롬프트를 빈값으로 저장 → 기본 프롬프트로 폴백 확인

### 피드백 수집 검증
- 챗봇 질문 → 답변 하단 👍/👎 버튼 표시 확인
- 👍 클릭 → 버튼 비활성화 + API 호출 성공 확인
- 👎 클릭 → 동일
- 이미 피드백한 메시지에 재클릭 불가 확인
- CHAT 라우팅 답변에 피드백 버튼 미표시 확인
- 직접 Ollama 모드에서 피드백 버튼 미표시 확인

### 대시보드 검증
- 관리자 설정 → 대시보드 → 피드백 섹션 표시 확인
- 라우팅별 만족도 비율 정확성 확인
- 최근 부정 피드백 목록 표시 확인
- 피드백 0건일 때 "아직 피드백이 없습니다" 표시 확인
- 라이트/다크 모드 정상 표시 확인
