/* ===================================
   Docker 전용 설정 파일
   Nginx가 /js/config.js 요청 시 이 파일로 오버라이드
   → 동일 포트 프록시이므로 backendUrl을 상대경로로 변경
   =================================== */

const AUTH_CONFIG = {
    enabled: true,
    loginRequired: true,
    backendUrl: '',                    // Nginx 동일 포트 → 상대경로
};

const AI_CONFIG = {
    enabled: true,
    useBackend: true,
    backendUrl: '',                    // Nginx 동일 포트 → 상대경로

    ollamaUrl: 'http://localhost:11434',
    model: 'gemma3:4b',

    searchType: 'hybrid',
    maxContextLength: 8000,
    maxSearchResults: 5,

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

const EDITOR_CONFIG = {
    enabled: true,
    requireAuth: true,
    backendUrl: '',                    // Nginx 동일 포트 → 상대경로
    autoSaveInterval: 30000,
    createBackup: true,
};

const UPLOAD_CONFIG = {
    enabled: true,
    requireAuth: true,
    backendUrl: '',                    // Nginx 동일 포트 → 상대경로
    acceptFormats: ['.docx', '.pdf'],
    maxFileSize: 500 * 1024 * 1024,
    autoSearchIndex: false,
    autoVectorIndex: false,
};

const DISPLAY_CONFIG = {
    platformName: "AHS's WebBook",
    siteTitle: 'WebBook',
    version: 'v5.5',
    tableStyle: 'bordered',
};
