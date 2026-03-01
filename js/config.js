/* ===================================
   설정 파일
   환경에 따라 이 파일만 수정하면 됩니다.
   =================================== */

const AUTH_CONFIG = {
    enabled: true,
    loginRequired: true,   // false: 열람 자유 (시범 운영용)
    backendUrl: 'http://localhost:8000',
};

const AI_CONFIG = {
    // AI 챗봇 활성화
    enabled: true,                          // false: 챗봇 아이콘 숨김

    // 백엔드 설정
    useBackend: true,                       // true: 백엔드 사용, false: Ollama 직접 호출
    backendUrl: 'http://localhost:8000',    // 회사: 'http://localhost:8000' 또는 서버 IP

    // Ollama 직접 호출 설정 (useBackend: false 일 때만 사용)
    ollamaUrl: 'http://localhost:11434',
    model: 'gemma3:4b',

    // 검색 설정
    searchType: 'hybrid',   // "keyword" | "vector" | "hybrid"

    // 채팅 설정
    maxContextLength: 8000,  // 컨텍스트로 전달할 최대 문자 수
    maxSearchResults: 5,     // 검색 결과 최대 개수

    // 시스템 프롬프트 (Ollama 직접 호출 시 사용)
    systemPrompt: `당신은 KF-21 전투기 기술 문서 전문 어시스턴트입니다. 제공된 참고 문서만을 기반으로 답변합니다.

[핵심 규칙]
1. 오직 제공된 문서 내용만 사용하여 답변합니다
2. 문서에 없는 내용은 절대 추측하지 않습니다
3. 정보가 없으면 "제공된 문서에서 해당 정보를 찾지 못했습니다"라고 답변합니다

[답변 방식]
- 핵심 내용을 먼저 간결하게 제시합니다
- 필요시 불릿 포인트나 번호 목록으로 구조화합니다
- 기술 용어는 문서에 표기된 그대로 사용합니다
- 답변 끝에 참고한 문서 제목을 명시합니다

[요청 유형별 대응]
- "요약해줘": 3~5문장으로 핵심만 간결하게 정리
- "핵심 내용": 중요 포인트를 불릿으로 5개 이내 나열
- "쉽게 설명해줘": 전문용어를 풀어서 비전문가도 이해할 수 있게 설명
- 일반 질문: 질문에 직접 답변 후 관련 맥락 보충

[언어]
한국어로 답변합니다.`
};

/* ===================================
   문서 편집기 설정
   =================================== */

const EDITOR_CONFIG = {
    // 편집 기능 활성화
    enabled: true,                          // true: 편집 버튼 표시

    // 인증 설정
    requireAuth: true,                      // true: 로그인 필요

    // 백엔드 설정
    backendUrl: 'http://localhost:8000',    // 저장 API 서버

    // 편집기 설정
    autoSaveInterval: 30000,                // 자동 저장 간격 (ms), 0이면 비활성화
    createBackup: true,                     // 저장 전 .bak 파일 생성
};

/* ===================================
   문서 업로드 설정
   =================================== */

const UPLOAD_CONFIG = {
    // 업로드 기능 활성화
    enabled: true,                          // true: 트리 메뉴에 업로드 버튼 표시

    // 인증 설정
    requireAuth: true,                      // true: 로그인 필요

    // 백엔드 설정
    backendUrl: 'http://localhost:8000',    // 업로드 API 서버

    // 허용 파일 형식
    acceptFormats: ['.docx', '.pdf'],       // 업로드 가능한 확장자

    // 업로드 제한
    maxFileSize: 500 * 1024 * 1024,         // 최대 파일 크기 (500MB)

    // 변환 후 자동 인덱싱 (false면 변환+메뉴갱신만 수행, 인덱싱은 스케줄링으로 별도 실행)
    autoSearchIndex: false,                  // true: 업로드 후 검색 인덱스 자동 재생성
    autoVectorIndex: false,                  // true: 업로드 후 벡터 인덱스 자동 재생성
};

/* ===================================
   콘텐츠 표시 설정
   =================================== */

const DISPLAY_CONFIG = {
    // 플랫폼 이름 (고정 — 푸터·로그인 하단에 "Powered by ___")
    platformName: "AHS's WebBook",

    // 사이트 타이틀 (헤더·로그인·document.title — 관리자 설정에서 변경 가능)
    siteTitle: 'WebBook',

    // 앱 버전 (푸터에 표시)
    version: 'v5.5',

    // 테이블 스타일: "bordered" | "simple" | "minimal"
    //   bordered — 모든 셀 테두리 + 네이비 헤더 (기본)
    //   simple   — 가로선만 + 볼드 헤더
    //   minimal  — 테두리 없음, 하단선만
    tableStyle: 'bordered',
};
