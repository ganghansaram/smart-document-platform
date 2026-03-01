# KF-21 History WebBook 설치 가이드 (폐쇄망 환경)

이 문서는 KF-21 History WebBook을 에어갭(폐쇄망) 환경에 설치하는 방법을 안내합니다.

---

## 목차

1. [준비물](#준비물)
2. [설치 단계](#설치-단계)
3. [서버 시작 및 종료](#서버-시작-및-종료)
4. [접속 확인](#접속-확인)
5. [문제 해결](#문제-해결)

---

## 준비물

폐쇄망으로 반입할 파일들:

### 필수 파일

1. **JDK (Java Development Kit)**
   - 파일명: `jdk-8u51-windows-x64.zip`
   - 버전: JDK 1.8.0_51

2. **Apache Tomcat**
   - 파일명: `apache-tomcat-7.0.77-windows-x64.zip`
   - 버전: 7.0.77

3. **KF-21 History WebBook**
   - 파일명: `kf21-webbook-template.zip`
   - 이 프로젝트 전체를 압축한 파일

### 선택 파일

- **Python 3.6 이상** (portable 버전 또는 설치 파일)
  - 파일명 예: `python-3.x.x-embed-amd64.zip`
  - 용도: 검색 인덱스 업데이트, 백엔드 서버, 문서 변환

> **참고:** 문서 업로드/변환 기능을 사용하려면 Python 패키지 오프라인 설치가 필요합니다. 자세한 내용은 [백엔드 설치 가이드](03-BACKEND-SETUP.md)의 "오프라인 패키지 다운로드" 섹션을 참조하세요.

---

## 설치 단계

### 1단계: JDK 설치

#### 1-1. JDK 압축 해제

```
C:\jdk1.8.0_51\
```

위치에 `jdk-8u51-windows-x64.zip` 파일을 압축 해제합니다.

**예시 디렉터리 구조:**
```
C:\jdk1.8.0_51\
├── bin\
│   ├── java.exe
│   └── javac.exe
├── lib\
└── ...
```

#### 1-2. JAVA_HOME 환경변수 설정

1. **시스템 속성 열기**
   - `Win + Pause` 또는 `내 PC 우클릭 > 속성`
   - `고급 시스템 설정` 클릭
   - `환경 변수` 버튼 클릭

2. **시스템 변수 추가**
   - `새로 만들기` 클릭
   - 변수 이름: `JAVA_HOME`
   - 변수 값: `C:\jdk1.8.0_51`
   - `확인` 클릭

3. **Path 변수 수정**
   - `시스템 변수`에서 `Path` 선택 후 `편집`
   - `새로 만들기` 클릭
   - `%JAVA_HOME%\bin` 추가
   - `확인` 클릭

#### 1-3. 설치 확인

명령 프롬프트(cmd)를 **새로** 열고 확인:

```cmd
java -version
```

**출력 예시:**
```
java version "1.8.0_51"
Java(TM) SE Runtime Environment (build 1.8.0_51-b16)
```

---

### 2단계: Tomcat 설치

#### 2-1. Tomcat 압축 해제

```
C:\apache-tomcat-7.0.77\
```

위치에 `apache-tomcat-7.0.77-windows-x64.zip` 파일을 압축 해제합니다.

**예시 디렉터리 구조:**
```
C:\apache-tomcat-7.0.77\
├── bin\
│   ├── startup.bat
│   └── shutdown.bat
├── conf\
├── webapps\
│   └── ROOT\
├── logs\
└── ...
```

#### 2-2. 설치 확인

```cmd
cd C:\apache-tomcat-7.0.77\bin
version.bat
```

**출력 예시:**
```
Server version: Apache Tomcat/7.0.77
```

---

### 3단계: 웹북 배포

#### 3-1. 기존 ROOT 백업 (선택사항)

```cmd
cd C:\apache-tomcat-7.0.77\webapps
rename ROOT ROOT.backup
mkdir ROOT
```

#### 3-2. 웹북 파일 복사

**방법 A: 압축 파일에서 직접 복사**

`kf21-webbook-template.zip` 압축 해제 후:

```cmd
# kf21-webbook-template 폴더의 모든 내용을 ROOT로 복사
xcopy /E /I /Y kf21-webbook-template\* C:\apache-tomcat-7.0.77\webapps\ROOT\
```

**방법 B: 탐색기에서 복사**

1. `kf21-webbook-template` 폴더 열기
2. 모든 파일 및 폴더 선택 (Ctrl+A)
3. 복사 (Ctrl+C)
4. `C:\apache-tomcat-7.0.77\webapps\ROOT\` 폴더 열기
5. 붙여넣기 (Ctrl+V)

#### 3-3. 배포 확인

`C:\apache-tomcat-7.0.77\webapps\ROOT\` 폴더에 다음 파일들이 있는지 확인:

```
ROOT\
├── index.html
├── css\            # main.css, content.css, editor.css 등
├── js\             # app.js, editor.js 등
├── data\           # menu.json, search-index.json
├── contents\       # HTML 콘텐츠
├── backend\        # FastAPI 백엔드 (AI/편집 사용 시)
└── ...
```

---

## 서버 시작 및 종료

### 서버 시작

#### 방법 1: 배치 파일 실행 (권장)

```cmd
C:\apache-tomcat-7.0.77\bin\startup.bat
```

실행하면 새 창이 열리며 로그가 출력됩니다.

**성공 메시지:**
```
INFO: Server startup in XXXX ms
```

#### 방법 2: 탐색기에서 실행

1. `C:\apache-tomcat-7.0.77\bin` 폴더 열기
2. `startup.bat` 더블클릭

---

### 서버 종료

#### 방법 1: 배치 파일 실행 (권장)

```cmd
C:\apache-tomcat-7.0.77\bin\shutdown.bat
```

#### 방법 2: 탐색기에서 실행

1. `C:\apache-tomcat-7.0.77\bin` 폴더 열기
2. `shutdown.bat` 더블클릭

#### 방법 3: Tomcat 창 닫기

startup.bat으로 실행한 검은 창을 닫으면 서버가 종료됩니다.

---

## 접속 확인

### 1. 로컬에서 접속

서버 시작 후 웹 브라우저(Chrome, Edge, Firefox)를 열고:

```
http://localhost:8080
```

또는

```
http://127.0.0.1:8080
```

**KF-21 History WebBook 메인 페이지**가 나타나면 성공입니다.

---

### 2. 다른 PC에서 접속

#### 2-1. 서버 PC의 IP 주소 확인

명령 프롬프트에서:

```cmd
ipconfig
```

**IPv4 주소** 확인 (예: `192.168.1.100`)

#### 2-2. 방화벽 설정

**Windows 방화벽에서 8080 포트 허용:**

```cmd
netsh advfirewall firewall add rule name="Tomcat HTTP" dir=in action=allow protocol=TCP localport=8080
```

또는 GUI로 설정:

1. `제어판 > Windows Defender 방화벽`
2. `고급 설정`
3. `인바운드 규칙 > 새 규칙`
4. `포트` 선택 > `TCP` > `특정 로컬 포트: 8080`
5. `연결 허용` > 이름: `Tomcat HTTP`

#### 2-3. 다른 PC에서 접속

같은 네트워크의 다른 PC 브라우저에서:

```
http://192.168.1.100:8080
```

(서버 IP 주소에 맞게 변경)

---

## 문제 해결

### 서버가 시작되지 않음

**증상:** `startup.bat` 실행 시 창이 바로 닫힘

**해결 방법:**

1. **JAVA_HOME 확인**
   ```cmd
   echo %JAVA_HOME%
   ```
   출력: `C:\jdk1.8.0_51` (정확한 경로)

2. **Java 실행 확인**
   ```cmd
   java -version
   ```

3. **포트 충돌 확인** (8080 포트가 이미 사용 중인지)
   ```cmd
   netstat -ano | findstr :8080
   ```

   다른 프로그램이 8080 포트를 사용 중이면:
   - 해당 프로그램 종료
   - 또는 Tomcat 포트 변경 (아래 참조)

4. **로그 확인**
   ```
   C:\apache-tomcat-7.0.77\logs\catalina.YYYY-MM-DD.log
   ```
   파일을 메모장으로 열어 오류 메시지 확인

---

### 페이지가 표시되지 않음

**증상:** `http://localhost:8080` 접속 시 "페이지를 찾을 수 없습니다"

**해결 방법:**

1. **서버 실행 확인**
   ```cmd
   netstat -ano | findstr :8080
   ```
   출력이 있으면 서버 실행 중

2. **브라우저 캐시 삭제**
   - Ctrl + F5 (강력 새로고침)

3. **웹북 파일 확인**
   - `C:\apache-tomcat-7.0.77\webapps\ROOT\index.html` 파일 존재 확인

---

### 메뉴가 표시되지 않음

**증상:** 좌측 메뉴가 비어있거나 "로딩 중..." 계속 표시

**해결 방법:**

1. **브라우저 개발자 도구 확인** (F12)
   - Console 탭에서 오류 메시지 확인

2. **menu.json 파일 확인**
   - `C:\apache-tomcat-7.0.77\webapps\ROOT\data\menu.json` 존재 확인

3. **JSON 문법 오류 확인**
   - 온라인 JSON 검증기(jsonlint.com)로 menu.json 검증

---

### 검색이 작동하지 않음

**증상:** 검색창에 입력해도 결과 없음

**해결 방법:**

1. **search-index.json 확인**
   - `C:\apache-tomcat-7.0.77\webapps\ROOT\data\search-index.json` 존재 확인

2. **검색 인덱스 재생성**
   - [사용자 가이드](04-USER-GUIDE.md)의 "검색 인덱스 업데이트" 참조

---

## 추가 설정 (선택사항)

### Tomcat 포트 변경

기본 포트 8080을 변경하려면:

1. `C:\apache-tomcat-7.0.77\conf\server.xml` 파일을 메모장으로 열기

2. 다음 부분 찾기:
   ```xml
   <Connector port="8080" protocol="HTTP/1.1"
   ```

3. 포트 번호 변경 (예: 9090):
   ```xml
   <Connector port="9090" protocol="HTTP/1.1"
   ```

4. 저장 후 Tomcat 재시작

5. 접속 주소: `http://localhost:9090`

---

### Windows 서비스로 등록 (자동 시작)

서버 재부팅 시 자동으로 Tomcat이 시작되도록 설정:

```cmd
cd C:\apache-tomcat-7.0.77\bin
service.bat install
```

**서비스 시작:**
```cmd
net start Tomcat7
```

**서비스 중지:**
```cmd
net stop Tomcat7
```

---

## 다음 단계

설치가 완료되었다면:

1. **[사용자 가이드](04-USER-GUIDE.md)** - 메뉴 추가 및 콘텐츠 관리 방법
2. **[빠른 시작](01-QUICK-START.md)** - 로컬 PC에서 간단히 테스트하는 방법
3. **[백엔드 설치](03-BACKEND-SETUP.md)** - AI 채팅 또는 문서 편집 기능 사용 시 필요

> **참고**: AI 채팅(`AI_CONFIG.enabled: true`) 또는 문서 편집(`EDITOR_CONFIG.enabled: true`) 기능을 사용하려면 FastAPI 백엔드 서버 설치가 필요합니다. 기본 웹북(메뉴, 검색, 콘텐츠 열람)은 Tomcat만으로 작동합니다.

---

## 요약: 최소 설치 절차

```cmd
1. JDK zip 압축 해제 → C:\jdk1.8.0_51
2. JAVA_HOME 환경변수 설정
3. Tomcat zip 압축 해제 → C:\apache-tomcat-7.0.77
4. 웹북 파일을 webapps\ROOT에 복사
5. C:\apache-tomcat-7.0.77\bin\startup.bat 실행
6. http://localhost:8080 접속
```

끝!
