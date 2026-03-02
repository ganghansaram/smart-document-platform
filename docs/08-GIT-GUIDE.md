# Git 및 GitHub 사용 가이드

이 문서는 Smart Document Platform 프로젝트의 버전 관리 및 GitHub 활용 방법을 안내합니다.

---

## 목차

1. [Git 저장소 개요](#git-저장소-개요)
2. [GitHub 저장소 생성 및 연결](#github-저장소-생성-및-연결)
3. [기본 작업 흐름](#기본-작업-흐름)
4. [변경사항 저장하기](#변경사항-저장하기)
5. [GitHub에 업로드하기](#github에-업로드하기)
6. [이전 버전으로 복구하기](#이전-버전으로-복구하기)
7. [팁과 모범 사례](#팁과-모범-사례)

---

## Git 저장소 개요

### 현재 상태

프로젝트는 이미 Git 저장소로 초기화되었으며, 모든 파일이 커밋되었습니다.

**확인 방법:**

```cmd
cd C:\AHS_Proj\smart-document-platform
git status
```

**출력 예시:**
```
On branch main
nothing to commit, working tree clean
```

---

## GitHub 저장소 생성 및 연결

### 1단계: GitHub에서 새 저장소 생성

1. **GitHub 로그인**: https://github.com
2. **새 저장소 생성**:
   - 우측 상단 `+` 클릭 → `New repository`
   - Repository name: `smart-document-platform` (또는 원하는 이름)
   - Description: `Air-gapped webbook template for KF-21 development documentation`
   - Visibility:
     - **Private** (비공개, 권장) - 내부 프로젝트용
     - **Public** (공개) - 오픈소스로 공개 시
   - **중요**: `Add a README file`, `.gitignore`, `license` 옵션 **체크 해제** (이미 로컬에 있음)
   - `Create repository` 클릭

### 2단계: 로컬 저장소와 GitHub 연결

GitHub에서 저장소 생성 후 표시되는 URL 복사 (예: `https://github.com/사용자명/smart-document-platform.git`)

**명령어 실행:**

```cmd
cd C:\AHS_Proj\smart-document-platform

# GitHub 저장소를 원격 저장소로 추가
git remote add origin https://github.com/사용자명/smart-document-platform.git

# 확인
git remote -v
```

**출력 예시:**
```
origin  https://github.com/사용자명/smart-document-platform.git (fetch)
origin  https://github.com/사용자명/smart-document-platform.git (push)
```

### 3단계: 초기 푸시

```cmd
# main 브랜치로 이름 변경 (GitHub 기본값)
git branch -M main

# GitHub에 업로드
git push -u origin main
```

GitHub 계정 인증 요구 시:
- **Username**: GitHub 사용자명
- **Password**: Personal Access Token (PAT) - GitHub Settings → Developer settings → Personal access tokens에서 생성

---

## 기본 작업 흐름

일반적인 개발 흐름:

```
1. 파일 수정
   ↓
2. 변경사항 확인 (git status)
   ↓
3. 변경사항 스테이징 (git add)
   ↓
4. 커밋 생성 (git commit)
   ↓
5. GitHub에 푸시 (git push)
```

---

## 변경사항 저장하기

### 1. 변경사항 확인

```cmd
git status
```

**출력 예시:**
```
modified:   contents/home.html
modified:   js/banner.js
```

### 2. 변경된 파일 추가

```cmd
# 특정 파일만 추가
git add contents/home.html js/banner.js

# 또는 모든 변경사항 추가
git add .
```

### 3. 커밋 생성

```cmd
git commit -m "배너 이미지 3개 추가 및 섹션 링크 자동 생성 기능 구현"
```

**커밋 메시지 작성 팁:**
- 무엇을 변경했는지 명확하게 작성
- 한글 또는 영어 사용 가능
- 50자 이내로 요약 (상세 설명은 본문에)

**상세한 커밋 메시지 작성:**

```cmd
git commit -m "배너 슬라이드쇼 기능 추가

- banner.js에 이미지 자동 전환 로직 구현
- 6초 간격 슬라이드 전환, 1초 페이드 효과
- 점 네비게이션으로 수동 이동 가능
- 홈페이지 섹션 링크를 menu.json에서 자동 생성"
```

---

## GitHub에 업로드하기

### 푸시 (업로드)

```cmd
git push
```

또는 처음 푸시하는 브랜치인 경우:

```cmd
git push -u origin main
```

### 풀 (다운로드)

다른 PC에서 작업한 내용을 가져오기:

```cmd
git pull
```

---

## 이전 버전으로 복구하기

### 1. 커밋 이력 확인

```cmd
git log --oneline
```

**출력 예시:**
```
a1b2c3d 배너 이미지 추가
e4f5g6h 초기 커밋
```

### 2. 특정 파일을 이전 버전으로 복구

```cmd
# 특정 파일을 마지막 커밋 상태로 되돌리기
git checkout -- contents/home.html

# 특정 파일을 특정 커밋 상태로 되돌리기
git checkout a1b2c3d -- contents/home.html
```

### 3. 전체 프로젝트를 이전 커밋으로 되돌리기

**방법 A: 작업 내용 유지하며 커밋만 되돌리기 (권장)**

```cmd
git reset --soft HEAD~1
```

**방법 B: 작업 내용 포함 완전히 되돌리기 (주의!)**

```cmd
# 위험: 모든 변경사항이 삭제됨
git reset --hard HEAD~1
```

### 4. 특정 커밋으로 새 브랜치 생성

```cmd
# 안전하게 이전 상태를 새 브랜치로 복사
git checkout -b backup-20250124 a1b2c3d
```

---

## 팁과 모범 사례

### 1. 자주 커밋하기

- 의미 있는 변경사항마다 커밋
- 한 번에 여러 기능을 섞지 말고 분리
- 예시:
  - ✅ "배너 이미지 3개 추가"
  - ✅ "검색 인덱스 업데이트"
  - ❌ "배너 추가하고 검색도 고치고 메뉴도 수정함"

### 2. 의미 있는 커밋 메시지

```
좋은 예:
- "홈페이지 배너 슬라이드쇼 기능 추가"
- "USER-GUIDE.md에 배너 이미지 관리 섹션 추가"

나쁜 예:
- "수정"
- "fix"
- "asdf"
```

### 3. 정기적으로 GitHub에 푸시

```cmd
# 하루 작업 종료 전 푸시
git push
```

백업 효과 + 다른 PC에서도 접근 가능

### 4. 브랜치 활용

새로운 기능 개발 시 브랜치 생성:

```cmd
# 새 기능 개발용 브랜치 생성
git checkout -b feature/advanced-search

# 작업 후 커밋
git add .
git commit -m "고급 검색 기능 구현"

# 메인 브랜치로 돌아가기
git checkout main

# 브랜치 병합
git merge feature/advanced-search
```

### 5. .gitignore 활용

불필요한 파일은 커밋하지 않기:

```
# .gitignore 파일에 추가
*.log
*.tmp
__pycache__/
```

### 6. 백업 브랜치 생성

중요한 변경 전 안전 브랜치 생성:

```cmd
git checkout -b backup-stable
git push -u origin backup-stable
git checkout main
```

---

## 자주 사용하는 명령어 요약

| 명령어 | 설명 |
|--------|------|
| `git status` | 현재 상태 확인 |
| `git add .` | 모든 변경사항 스테이징 |
| `git commit -m "메시지"` | 커밋 생성 |
| `git push` | GitHub에 업로드 |
| `git pull` | GitHub에서 다운로드 |
| `git log` | 커밋 이력 확인 |
| `git diff` | 변경사항 비교 |
| `git checkout -- 파일명` | 파일 되돌리기 |
| `git branch` | 브랜치 목록 확인 |
| `git checkout 브랜치명` | 브랜치 전환 |

---

## 문제 해결

### GitHub 푸시 시 인증 오류

**증상:**
```
remote: Support for password authentication was removed on August 13, 2021.
```

**해결:**
1. GitHub Settings → Developer settings → Personal access tokens
2. `Generate new token (classic)` 클릭
3. Scopes: `repo` 체크
4. 생성된 토큰을 비밀번호 대신 사용

---

### 충돌 (Conflict) 발생

**증상:**
```
CONFLICT (content): Merge conflict in contents/home.html
```

**해결:**
1. 충돌 파일 열기
2. `<<<<<<<`, `=======`, `>>>>>>>` 표시 찾기
3. 원하는 버전 선택하고 표시 제거
4. 저장 후 커밋

```cmd
git add contents/home.html
git commit -m "충돌 해결"
```

---

## 다음 단계

Git과 GitHub를 활용하면:
- ✅ 모든 변경 이력 추적 가능
- ✅ 언제든 이전 버전으로 복구 가능
- ✅ 여러 PC에서 동기화
- ✅ 팀원과 협업 가능

**권장 워크플로우:**
1. 매일 작업 시작 전: `git pull`
2. 작업 중: 의미 있는 단위로 `git commit`
3. 작업 종료 후: `git push`

---

더 많은 정보는 공식 Git 문서를 참조하세요:
- Git 공식 문서: https://git-scm.com/doc
- GitHub 가이드: https://docs.github.com/
