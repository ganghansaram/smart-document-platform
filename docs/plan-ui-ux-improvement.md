# UI/UX 개선 계획

> **상태**: 확정 (구현 대기)
> **작성일**: 2026-03-05
> **대상**: 플랫폼 전체 (Explorer, Translator, Settings, Launcher, Compare)

---

## 현황 요약

| 화면 | 헤더 방식 | 우측 Nav | 푸터 |
|------|-----------|----------|------|
| Explorer (index.html) | 커스텀 하드코딩 | Platform, Edit, Home, About, Bookmarks, Search, Login/Users, Theme | O (스크롤 시 노출) |
| Launcher (launcher.html) | platform-header 컴포넌트 | (없음) | X |
| Translator (translator.html) | platform-header 컴포넌트 | Platform, Home | X |
| Settings (admin.html) | platform-header 컴포넌트 | Platform | X |

**문제점**:
- 시스템 간 이동 시 항상 Launcher를 경유해야 함
- Explorer만 독자적 헤더 구조 (나머지는 platform-header 공유)
- Users(계정관리), Dashboard(대시보드)가 Explorer에만 존재
- 푸터가 Explorer에만 있고 다른 화면에는 없음
- 화면 추가 시마다 레이아웃 맞추는 데 비용이 큼

---

## 개선안 1: 관리 기능 통합 (Users, Dashboard → Settings) ✅ 확정

### 1-A. Users (계정관리) → Settings 이동

**현재**: Explorer 상단바의 "Users" 클릭 → 모달 팝업
**개선**: Settings(admin.html) 좌측 사이드바에 "계정 관리" 탭 추가 → 중앙 패널에 표시

| 항목 | 내용 |
|------|------|
| 위치 | Settings 사이드바 최상단 (공통 / Explorer / Translator 앞) |
| 화면 | 기존 모달 내용을 중앙 패널에 재배치 (사용자 목록 테이블 + 추가/수정/삭제) |
| Explorer 변경 | 상단바에서 "Users" 메뉴 제거 |

### 1-B. Dashboard → Settings 이동

**현재**: Explorer 좌측 트리 하단 "대시보드" → 중앙 패널에 렌더링
**개선**: Settings 좌측 사이드바에 "대시보드" 탭 추가 → 중앙 패널에 표시

| 항목 | 내용 |
|------|------|
| 위치 | Settings 사이드바 (계정 관리 다음) |
| 화면 | 기존 analytics.js 대시보드를 Settings 중앙 패널에 렌더링 |
| Explorer 변경 | 좌측 트리에서 "대시보드" 메뉴 제거 |
| 대시보드 내용 | 현행 유지 (구성 조정은 추후 논의) |

### Settings 사이드바 구조 (개선 후)

```
계정 관리          ← 신규
대시보드           ← Explorer에서 이동
─────────────────
공통 설정
Explorer 설정
Translator 설정
```

---

## 개선안 2: 시스템 스위처 (App Switcher) ✅ 확정

### 방식

헤더 좌측 로고 옆에 **격자 아이콘 (⠿)** 을 배치하고, 클릭 시 드롭다운으로 시스템 목록을 표시한다.

```
┌──────────────────────────────────────────────────────────┐
│ [KAI] Title  [⠿]              [기능메뉴들]  admin|Logout │
└──────────────────────────────────────────────────────────┘
                 ↓ 클릭 시
              ┌─────────────┐
              │ ◈ Platform   │
              │ 📖 Explorer  │
              │ 🔄 Translator│
              │ ⚙ Settings  │  ← admin 전용
              │ 📊 Compare   │  ← 향후
              └─────────────┘
```

- 현재 시스템은 드롭다운에서 하이라이트 표시
- 시스템 추가되어도 헤더 폭 변화 없음
- Google Workspace, Microsoft 365 등 익숙한 패턴

### 헤더 영역 재정의

```
[좌측 영역]                    [중앙]           [우측 영역]
 로고 + 타이틀 + 시스템스위처    (midSlot)        시스템 고유 기능 + Auth + Theme

좌측: 브랜드 + 시스템 이동 (공통)
중앙: 페이지 네비게이션 등 (시스템별 선택)
우측: 해당 시스템 기능 메뉴 + 인증 (시스템별)
```

**Explorer 우측 Nav** (개선 후):
```
Home | About | Bookmarks | Search | Edit(편집자) | Theme | admin | Logout
```
- "Platform" 제거 (시스템 스위처로 대체)
- "Users" 제거 (Settings로 이동)

---

## 개선안 3: Explorer 헤더 → platform-header 통합 ✅ 확정

### 배경

현재 Explorer(index.html)만 독자적 하드코딩 헤더를 사용하고, 나머지 3개 화면은 `platform-header.css` + `initPlatformHeader()` 컴포넌트를 공유한다. 이로 인해:
- 시스템 스위처를 Explorer에 적용하려면 별도 구현 필요
- 헤더 스타일 변경 시 Explorer만 따로 수정해야 함
- 새 화면 추가 시 기존 레이아웃 맞추는 비용 증가

### 방침

Explorer 헤더를 `platform-header` 컴포넌트로 통합한다.
- `initPlatformHeader()` API를 확장하여 Explorer의 기능 메뉴(Home, About, Bookmarks, Search, Edit)를 `navItems`로 전달
- Explorer 고유 기능(검색 오버레이, 북마크 오버레이, 에디터)은 기존 JS 모듈이 처리 — 헤더는 트리거 역할만
- 시스템 스위처가 자동 적용됨

### 추가 최적화 대상

헤더 통합 과정에서 다른 공통 모듈도 정리가 필요할 수 있다:
- CSS 중복 제거 (index.html 인라인 헤더 스타일 → platform-header.css)
- 인증 흐름 통일 (auth.js의 헤더 DOM 조작 → platform-header 콜백)
- 기타 소스코드 최적화 (구현 시 파악)

---

## 개선안 4: 푸터 표준화 ✅ 확정

### 현황

Explorer의 푸터는 중앙 패널(`#content-panel`) 안에 위치하며, **기본 화면에서는 노출되지 않고 스크롤 시에만 나타나는** 설계이다. (`margin-top: 60px`, 음수 마진으로 패널 전폭 확장, `content.css:1019`)

```
┌─────────────────────────────────┐
│  콘텐츠                          │  ← 뷰포트
│                                 │
│                                 │
├─────────────────────────────────┤
│  © KAI · 연락처 · 버전           │  ← 스크롤해야 보임
└─────────────────────────────────┘
```

### 방침

Explorer의 "스크롤 시 노출" 패턴을 유지하면서, 공통 푸터 모듈로 분리하여 전 시스템에 적용한다.

| 항목 | 기준 |
|------|------|
| 내용 | `© {년도} Korea Aerospace Industries, Ltd. · Smart Document Platform` |
| 위치 | 콘텐츠 영역 최하단 (스크롤 시 노출, 고정 아님) |
| 스타일 | Explorer 현행 푸터 디자인 기반, 공통 CSS로 분리 |
| 연락처/버전 | Explorer에만 유지하거나 About 페이지로 이동 (추후 결정) |
| 적용 | 전 시스템 (Explorer, Translator, Settings, Launcher) |
| 구현 | 공통 JS 함수 또는 HTML 템플릿으로 한 곳에서 관리 |

> Compare 등 신규 시스템 도입 시에도 이 기준을 적용한다.

---

## 구현 우선순위

| 순서 | 항목 | 난이도 | 영향 범위 | 비고 |
|------|------|--------|-----------|------|
| 1 | Explorer 헤더 → platform-header 통합 | 고 | index.html 헤더 리팩토링 | 2번의 전제 조건 |
| 2 | 시스템 스위처 (platform-header 확장) | 중 | 전 시스템 헤더 | 1번 완료 후 전 화면 일괄 적용 |
| 3 | Users → Settings 이동 | 중 | admin.html, index.html, auth.js | |
| 4 | Dashboard → Settings 이동 | 중 | admin.html, index.html, analytics.js | |
| 5 | 푸터 공통 모듈화 + 전 시스템 적용 | 저 | 전 시스템 | |

> 1→2는 순서 의존. 3, 4는 독립적으로 병행 가능. 5는 언제든 가능.

---

## 미결 사항

- [ ] Explorer 푸터의 연락처/버전 정보를 다른 시스템에도 표시할지 결정
- [ ] 대시보드 콘텐츠 구성 조정 범위
- [ ] Compare 시스템 도입 시점 및 내비게이션 포함 여부

---

## 진행 체크리스트

### 개선안 1: 관리 기능 통합
- [ ] Settings 사이드바에 "계정 관리" 탭 추가
- [ ] Users 모달 내용을 Settings 중앙 패널로 이식
- [ ] Explorer 상단바에서 "Users" 메뉴 제거
- [ ] Settings 사이드바에 "대시보드" 탭 추가
- [ ] analytics.js 대시보드를 Settings 중앙 패널로 이식
- [ ] Explorer 좌측 트리에서 "대시보드" 메뉴 제거
- [ ] Explorer menu.json에서 대시보드 시스템 항목 제거

### 개선안 2: 시스템 스위처
- [ ] platform-header에 시스템 스위처 아이콘 + 드롭다운 구현
- [ ] 현재 시스템 하이라이트 표시
- [ ] admin 전용 항목 (Settings) 권한 처리
- [ ] 전 시스템에서 기존 "Platform" 링크 제거
- [ ] Explorer 헤더에 시스템 스위처 적용

### 개선안 3: Explorer 헤더 통합
- [ ] initPlatformHeader() API 확장 (Explorer 기능 메뉴 지원)
- [ ] Explorer 하드코딩 헤더 → platform-header 호출로 교체
- [ ] 검색/북마크/에디터 트리거 연결 확인
- [ ] 인증 흐름 (auth.js) 헤더 DOM 조작 정리
- [ ] Explorer 인라인 헤더 CSS 제거/통합
- [ ] 기타 소스코드 최적화

### 개선안 4: 푸터 표준화
- [ ] 공통 푸터 모듈 (JS 함수 또는 HTML 템플릿) 작성
- [ ] 공통 푸터 CSS 분리 (content.css → platform-footer.css)
- [ ] Explorer 기존 푸터를 공통 모듈로 교체
- [ ] Translator에 공통 푸터 적용
- [ ] Settings에 공통 푸터 적용
- [ ] Launcher에 공통 푸터 적용
- [ ] "스크롤 시 노출" 동작 전 시스템 확인
