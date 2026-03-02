# Smart Document Platform 빠른 시작 (로컬 테스트)

이 문서는 Tomcat 설치 없이 로컬 PC에서 Smart Document Platform을 빠르게 테스트하는 방법을 안내합니다.

---

## 목차

1. [개요](#개요)
2. [Python 설치 확인](#python-설치-확인)
3. [서버 시작](#서버-시작)
4. [접속 확인](#접속-확인)
5. [서버 종료](#서버-종료)
6. [문제 해결](#문제-해결)

---

## 개요

### 이 방법은 언제 사용하나요?

- ✅ **로컬 PC에서 빠르게 테스트**할 때
- ✅ **메뉴나 콘텐츠 수정 후 즉시 확인**할 때
- ✅ **Tomcat 설치 없이 간단히 확인**하고 싶을 때

### 주의사항

- ⚠️ 이 방법은 **개발/테스트 전용**입니다
- ⚠️ **실제 서비스**에는 [02-INSTALLATION.md](02-INSTALLATION.md)의 Tomcat 방식 사용
- ⚠️ 서버 재부팅 시 자동으로 시작되지 않음

---

## Python 설치 확인

### 1. Python이 설치되어 있는지 확인

명령 프롬프트(cmd)를 열고:

```cmd
python --version
```

**출력 예시:**
```
Python 3.x.x
```

### 2. Python이 없는 경우

**방법 A: 공식 사이트에서 다운로드**

1. https://www.python.org/downloads/ 접속
2. "Download Python" 클릭하여 설치 파일 다운로드
3. 설치 시 **"Add Python to PATH"** 체크 필수!

**방법 B: Microsoft Store에서 설치 (Windows 10/11)**

1. `시작 메뉴` > `Microsoft Store`
2. "Python" 검색
3. "Python 3.x" 설치

**폐쇄망 환경:**

- 외부에서 Python 설치 파일을 다운로드하여 폐쇄망으로 반입
- Portable Python(임베디드 버전)도 사용 가능

---

## 서버 시작

### 1단계: 프로젝트 폴더로 이동

명령 프롬프트(cmd)에서 웹북 프로젝트 폴더로 이동:

```cmd
cd C:\path\to\smart-document-platform
```

**예시:**
```cmd
cd C:\Users\사용자명\Desktop\smart-document-platform
```

### 2단계: Python 웹 서버 실행

```cmd
python -m http.server 8080
```

**출력 예시:**
```
Serving HTTP on :: port 8080 (http://[::]:8080/) ...
```

이 메시지가 나타나면 서버가 실행된 것입니다!

### 다른 포트 사용하기

8080 포트가 사용 중이면 다른 포트 번호 사용:

```cmd
python -m http.server 9000
```

---

## 접속 확인

### 1. 웹 브라우저 열기

Chrome, Edge, Firefox 중 하나를 실행

### 2. 주소 입력

```
http://localhost:8080
```

또는

```
http://127.0.0.1:8080
```

### 3. 확인

**Smart Document Platform 메인 페이지**가 나타나면 성공!

---

## 파일 수정 후 확인

### 수정 작업 흐름

1. **파일 수정**
   - `data/menu.json` 수정
   - `contents/` 폴더에 HTML 추가
   - CSS/JS 수정 등

2. **브라우저에서 새로고침**
   - `F5` 또는 `Ctrl + F5` (강력 새로고침)

3. **변경 사항 즉시 확인**

**서버 재시작 불필요!** 파일 수정 후 브라우저 새로고침만 하면 됩니다.

---

## 서버 종료

### 방법 1: Ctrl + C

명령 프롬프트 창에서:

```
Ctrl + C
```

**확인 메시지:**
```
Terminate batch job (Y/N)? Y
```

`Y` 입력 후 Enter

### 방법 2: 창 닫기

명령 프롬프트 창을 닫으면 서버가 자동으로 종료됩니다.

---

## 다른 PC에서 접속하기

### 1. 현재 PC의 IP 주소 확인

**명령 프롬프트:**
```cmd
ipconfig
```

**IPv4 주소 확인 (예: 192.168.1.100)**

### 2. 방화벽 설정

**Windows 방화벽에서 8080 포트 허용:**

```cmd
netsh advfirewall firewall add rule name="Python HTTP Server" dir=in action=allow protocol=TCP localport=8080
```

### 3. 다른 PC에서 접속

같은 네트워크의 다른 PC 브라우저에서:

```
http://192.168.1.100:8080
```

(IP 주소는 실제 값으로 변경)

---

## 문제 해결

### 서버가 시작되지 않음

**증상 1:** `python: command not found` 또는 `'python'은(는) 내부 또는 외부 명령...`

**해결:**
- Python이 설치되지 않았거나 PATH에 등록되지 않음
- `python3 -m http.server 8080` 시도 (Linux/Mac)
- Python 재설치 (PATH 옵션 체크)

**증상 2:** `OSError: [Errno 48] Address already in use`

**해결:**
- 8080 포트가 이미 사용 중
- 다른 포트 사용: `python -m http.server 9000`

---

### 페이지가 표시되지 않음

**증상:** "페이지를 찾을 수 없습니다" 오류

**해결:**

1. **서버 실행 확인**
   - 명령 프롬프트 창이 열려 있는지 확인
   - "Serving HTTP..." 메시지가 보이는지 확인

2. **폴더 위치 확인**
   - 서버를 실행한 폴더에 `index.html` 파일이 있는지 확인
   - 잘못된 폴더에서 실행한 경우 종료 후 올바른 폴더에서 재실행

3. **브라우저 캐시**
   - `Ctrl + F5` (강력 새로고침)

---

### 파일 수정이 반영되지 않음

**증상:** CSS/JS 파일을 수정했는데 변경 사항이 안 보임

**해결:**

1. **강력 새로고침**
   - `Ctrl + Shift + R` (Chrome/Firefox)
   - `Ctrl + F5` (Edge)

2. **브라우저 캐시 삭제**
   - Chrome: `Ctrl + Shift + Delete` > 캐시된 이미지 및 파일 삭제

3. **개발자 도구에서 캐시 비활성화**
   - `F12` > Network 탭 > "Disable cache" 체크

---

### 다른 PC에서 접속 안 됨

**해결:**

1. **같은 네트워크인지 확인**
   - 같은 WiFi 또는 유선 네트워크 사용 중인지 확인

2. **방화벽 확인**
   - Windows 방화벽에서 8080 포트 허용했는지 확인
   - 일시적으로 방화벽 끄고 테스트 (주의: 테스트 후 다시 켜기)

3. **IP 주소 재확인**
   - `ipconfig`로 정확한 IP 주소 다시 확인

---

## Python 웹 서버 vs Tomcat

| 항목 | Python 웹 서버 | Tomcat |
|------|---------------|--------|
| **설치** | Python만 있으면 됨 | JDK + Tomcat 설치 필요 |
| **실행** | 명령어 한 줄 | startup.bat 실행 |
| **용도** | 개발/테스트 | 실제 서비스 |
| **성능** | 낮음 | 높음 |
| **자동 시작** | 없음 | Windows 서비스 등록 가능 |
| **동시 접속** | 제한적 | 안정적 |

**결론:**
- 개인 PC에서 혼자 테스트 → **Python 웹 서버**
- 회사에서 여러 사람이 사용 → **Tomcat**

---

## 검색 인덱스 업데이트

문서를 추가/수정한 후 검색 기능 업데이트:

```cmd
# 프로젝트 폴더에서
python tools\build-search-index.py
```

**출력:**
```
============================================================
Smart Document Platform - 검색 인덱스 생성
============================================================

인덱싱: contents/home.html - Smart Document Platform에 오신 것을 환영합니다
...
검색 인덱스 생성 완료: data/search-index.json
총 X개의 문서가 인덱싱되었습니다.

완료!
```

---

## 요약: 가장 빠른 테스트 방법

```cmd
# 1. 프로젝트 폴더로 이동
cd C:\path\to\smart-document-platform

# 2. 서버 실행
python -m http.server 8080

# 3. 브라우저 열고 접속
http://localhost:8080

# 4. 테스트 완료 후 종료
Ctrl + C
```

끝!

---

## 다음 단계

- **메뉴 추가하기**: [사용자 가이드](04-USER-GUIDE.md)
- **실제 서비스 배포**: [설치 가이드](02-INSTALLATION.md)
