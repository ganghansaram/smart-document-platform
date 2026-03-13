/* ===================================
   관리자 설정 페이지 — renderAdminSettings()
   =================================== */

// ── showToast 폴백 (admin.html에서 app.js 미로드 시) ──────────────────────────
if (typeof showToast === 'undefined') {
    window.showToast = function(message, type) {
        var toast = document.getElementById('app-toast');
        if (!toast) {
            toast = document.createElement('div');
            toast.id = 'app-toast';
            toast.className = 'toast';
            document.body.appendChild(toast);
        }
        clearTimeout(toast._timer);
        toast.textContent = message;
        toast.className = 'toast' + (type ? ' ' + type : '') + ' show';
        toast._timer = setTimeout(function() { toast.classList.remove('show'); }, 3000);
    };
}

// ── 재시작 대기 상태 (페이지 재진입 시 배너 복원용) ──────────────────────────
var _pendingRestartItems = [];

// ── 설정 스키마 (시스템 > 탭 2-depth) ────────────────────────────────────────
var SETTINGS_SCHEMA = {
    systems: [
        {
            id: 'users',
            label: '계정 관리',
            custom: true,
            group: '관리',
        },
        {
            id: 'dashboard',
            label: '대시보드',
            custom: true,
            group: '관리',
        },
        {
            id: 'common',
            label: '공통',
            group: '시스템 설정',
            tabs: [
                {
                    tabId: 'tab-security',
                    tabLabel: '보안 / 접근',
                    sections: [
                        {
                            title: '접근 제어',
                            fields: [
                                { group: 'security', key: 'login_required', label: '열람 로그인 필수 (백엔드)', type: 'toggle',
                                  restart: true, desc: '활성화 시 비로그인 사용자의 API 접근 차단. 변경 후 서버 재시작 필요' },
                                { group: 'security', key: 'cors_origins',   label: 'CORS 허용 출처',            type: 'textarea',
                                  restart: true,
                                  desc: '허용할 출처 URL (줄바꿈으로 구분). 변경 후 서버 재시작 필요',
                                  toStr: function(arr) { return Array.isArray(arr) ? arr.join('\n') : String(arr || ''); },
                                  fromStr: function(s) { return s.split('\n').map(function(v) { return v.trim(); }).filter(Boolean); }
                                },
                            ]
                        }
                    ]
                }
            ]
        },
        {
            id: 'explorer',
            label: 'Explorer',
            group: '시스템 설정',
            tabs: [
                {
                    tabId: 'tab-ai',
                    tabLabel: 'AI / RAG',
                    sections: [
                        {
                            title: '모델 연결',
                            fields: [
                                { group: 'ai', key: 'ollama_url',      label: 'Ollama URL',   type: 'text',   restart: true,
                                  desc: '로컬 Ollama 서버 주소 (예: http://localhost:11434)' },
                                { group: 'ai', key: 'ollama_model',    label: 'LLM 모델',     type: 'text',   restart: true,
                                  desc: '챗봇에 사용할 Ollama 모델명 (예: gemma3:4b, llama3:8b)' },
                                { group: 'ai', key: 'embedding_model', label: '임베딩 모델',  type: 'text',   restart: true,
                                  desc: '벡터 검색에 사용할 임베딩 모델 (예: bge-m3)' },
                            ]
                        },
                        {
                            title: '검색 설정',
                            fields: [
                                { group: 'ai', key: 'default_search_type',   label: '검색 방식',          type: 'select',
                                  options: [['hybrid','하이브리드 (권장)'], ['keyword','키워드 (BM25)'], ['vector','벡터 유사도']],
                                  restart: false, desc: '문서 검색 알고리즘 선택' },
                                { group: 'ai', key: 'max_search_results',    label: '최대 검색 결과 수',  type: 'number',
                                  restart: false, min: 1, max: 20, step: 1,
                                  desc: '챗봇 답변 생성 시 참조할 최대 문서 청크 수' },
                                { group: 'ai', key: 'max_context_length',    label: '최대 컨텍스트 길이', type: 'number',
                                  restart: false, min: 1000, max: 32000, step: 500,
                                  desc: 'LLM에 전달하는 참고문서 최대 글자 수 (토큰 예산)' },
                                { group: 'ai', key: 'hybrid_keyword_weight', label: '키워드 비중 (하이브리드)', type: 'number',
                                  restart: false, min: 0, max: 1, step: 0.05,
                                  desc: '하이브리드 검색에서 BM25(키워드) 비중. 나머지는 벡터 비중 (예: 0.3 → 키워드 30%, 벡터 70%)' },
                                { group: 'ai', key: 'hybrid_rrf_k',         label: 'RRF K 값',           type: 'number',
                                  restart: false, min: 1, max: 200, step: 1,
                                  desc: 'Reciprocal Rank Fusion 상수. 작을수록 상위 순위 문서 가중치 증가 (기본 60)' },
                                { group: 'ai', key: 'min_vector_score',     label: '최소 벡터 유사도',   type: 'number',
                                  restart: false, min: 0, max: 1, step: 0.01,
                                  desc: '이 값 미만의 벡터 유사도 결과는 제외. 관련 없는 결과 필터링 (기본 0.48)' },
                            ]
                        },
                        {
                            title: '리랭커 / 쿼리 재작성',
                            fields: [
                                { group: 'ai', key: 'reranker_enabled',          label: '리랭커 사용',      type: 'toggle',
                                  restart: false, desc: 'Cross-encoder 리랭커(bge-reranker-v2-m3)로 검색 결과 정확도 향상' },
                                { group: 'ai', key: 'reranker_top_k_multiplier', label: '리랭커 후보 배수', type: 'number',
                                  restart: false, min: 1, max: 10, step: 1,
                                  desc: '리랭커 입력 후보 수 = 최대 검색 결과 × 이 값 (더 많은 후보에서 선별)' },
                                { group: 'ai', key: 'query_rewrite_enabled',     label: '쿼리 재작성',      type: 'toggle',
                                  restart: false, desc: '멀티턴 대화에서 이전 문맥을 반영한 독립적 검색 쿼리 자동 재작성' },
                            ]
                        },
                        {
                            title: '챗봇 프롬프트',
                            fields: [
                                { group: 'ai', key: 'chat_system_prompt', label: '시스템 프롬프트 (백엔드 RAG)',
                                  type: 'textarea', restart: false, rows: 12,
                                  placeholder: '당신은 KF-21 전투기 기술 문서 전문 어시스턴트입니다. 제공된 참고 문서만을 기반으로 답변합니다.\n\n[핵심 규칙]\n1. 오직 제공된 문서 내용만 사용하여 답변합니다\n2. 문서에 없는 내용은 절대 추측하거나 일반 지식으로 보충하지 않습니다\n3. 정보가 없으면 "제공된 문서에서 해당 정보를 찾지 못했습니다"라고만 답변하고 끝냅니다\n4. "하지만", "일반적으로", "참고로" 등으로 문서 외 지식을 덧붙이지 않습니다\n\n[답변 형식]\n- 마크다운으로 답변합니다: **굵게**와 목록(- 또는 1.)만 사용합니다\n- 핵심 내용을 먼저 간결하게 제시하고, 필요한 경우만 목록으로 구조화합니다\n\n[언어]\n반드시 한국어로 답변합니다. 참고 문서가 영어여도 한국어로 번역하여 답변합니다.',
                                  desc: '챗봇이 답변 생성 시 따르는 지침. 비워두면 회색 글씨의 기본 프롬프트가 적용됩니다.' },
                            ]
                        },
                    ]
                },
                {
                    tabId: 'tab-session',
                    tabLabel: '세션',
                    sections: [
                        {
                            title: '대화 세션 (인메모리)',
                            fields: [
                                { group: 'session', key: 'max_conversation_turns', label: '최대 대화 턴 수',      type: 'number',
                                  restart: false, min: 1, max: 20, step: 1,
                                  desc: '챗봇이 기억할 최대 대화 교환 횟수 (이전 Q&A 쌍)' },
                                { group: 'session', key: 'max_history_length',     label: '히스토리 최대 길이',   type: 'number',
                                  restart: false, min: 100, max: 10000, step: 100,
                                  desc: 'LLM에 포함되는 대화 히스토리 최대 글자 수' },
                                { group: 'session', key: 'max_sessions',           label: '최대 세션 수',         type: 'number',
                                  restart: false, min: 1, max: 1000, step: 10,
                                  desc: '서버 메모리에 동시 유지할 최대 대화 세션 수 (초과 시 LRU 방식으로 오래된 세션 제거)' },
                                { group: 'session', key: 'max_idle_minutes',       label: '유휴 세션 만료 (분)', type: 'number',
                                  restart: false, min: 1, max: 1440, step: 5,
                                  desc: '마지막 메시지 이후 이 시간(분)이 지나면 세션 자동 삭제' },
                            ]
                        },
                        {
                            title: '로그인 세션',
                            fields: [
                                { group: 'session', key: 'session_expiry_hours', label: '로그인 세션 만료 (시간)', type: 'number',
                                  restart: true, min: 1, max: 720, step: 1,
                                  desc: '로그인 유지 시간. 이 시간이 지나면 자동 로그아웃 처리 (재시작 필요)' },
                            ]
                        }
                    ]
                },
                {
                    tabId: 'tab-upload',
                    tabLabel: '업로드',
                    sections: [
                        {
                            title: '업로드 기능',
                            fields: [
                                { group: 'frontend', key: 'upload_enabled',           label: '업로드 기능 활성화',             type: 'toggle',
                                  restart: false, desc: 'Editor 이상 권한 사용자의 파일 업로드 UI 표시 여부' },
                                { group: 'frontend', key: 'upload_max_file_size_mb',  label: '최대 파일 크기 (MB)',            type: 'number',
                                  restart: false, min: 1, max: 2000, step: 10,
                                  desc: '업로드 허용 최대 단일 파일 크기 (MB 단위)' },
                                { group: 'frontend', key: 'upload_auto_search_index', label: '업로드 후 검색 인덱스 자동 갱신', type: 'toggle',
                                  restart: false, desc: '파일 업로드 완료 후 키워드(BM25) 검색 인덱스 자동 재생성' },
                                { group: 'frontend', key: 'upload_auto_vector_index', label: '업로드 후 벡터 인덱스 자동 갱신', type: 'toggle',
                                  restart: false, desc: '파일 업로드 완료 후 FAISS 벡터 인덱스 자동 재생성 (시간 소요)' },
                            ]
                        },
                        {
                            title: 'DOCX 변환',
                            fields: [
                                { group: 'upload', key: 'word_com_preprocess', label: 'Word COM 전처리', type: 'toggle',
                                  restart: false, desc: 'DOCX 변환 시 Microsoft Word COM으로 자동 번호(장절 목차 등) 평문화. Windows + Word 설치 필요' },
                                { group: 'upload', key: 'upload_temp_dir',     label: '임시 폴더 경로',  type: 'text',
                                  restart: false, desc: '업로드 파일 임시 저장 경로 (비워두면 시스템 기본 임시 폴더 사용)' },
                            ]
                        }
                    ]
                },
                {
                    tabId: 'tab-frontend',
                    tabLabel: '화면 / 에디터',
                    sections: [
                        {
                            title: '화면 표시',
                            fields: [
                                { group: 'frontend', key: 'display_site_title',  label: '사이트 타이틀', type: 'text',
                                  restart: false, desc: '헤더·로그인 페이지·브라우저 탭에 표시되는 사이트 이름 (예: KF-21 History WebBook)' },
                                { group: 'frontend', key: 'display_table_style', label: '테이블 스타일', type: 'select',
                                  options: [['bordered','Bordered — 테두리형 (기본)'], ['simple','Simple — 심플'], ['minimal','Minimal — 최소']],
                                  restart: false, desc: '문서 내 테이블의 표시 스타일 프리셋' },
                                { group: 'frontend', key: 'login_required',      label: '열람 로그인 필수 (프론트엔드)', type: 'toggle',
                                  restart: false, desc: '프론트엔드 측 로그인 게이트 여부. 보안 탭의 백엔드 설정과 동일하게 유지 권장' },
                            ]
                        },
                        {
                            title: 'AI 챗봇 (프론트엔드)',
                            fields: [
                                { group: 'frontend', key: 'ai_enabled',             label: '챗봇 표시',            type: 'toggle',
                                  restart: false, desc: '우측 하단 AI 챗봇 버튼 및 패널 표시 여부' },
                                { group: 'frontend', key: 'ai_use_backend',          label: '백엔드 RAG 사용',      type: 'toggle',
                                  restart: false, desc: '활성화 시 서버 RAG 파이프라인 사용 / 비활성화 시 브라우저에서 Ollama 직접 호출' },
                                { group: 'frontend', key: 'ai_search_type',          label: '검색 방식 (직접 모드)', type: 'select',
                                  options: [['hybrid','하이브리드'], ['keyword','키워드'], ['vector','벡터']],
                                  restart: false, desc: '백엔드 미사용 시 프론트엔드 직접 검색 방식 (백엔드 RAG 사용 시 무관)' },
                                { group: 'frontend', key: 'ai_max_search_results',   label: '최대 검색 결과 수',    type: 'number',
                                  restart: false, min: 1, max: 20, step: 1 },
                                { group: 'frontend', key: 'ai_max_context_length',   label: '최대 컨텍스트 길이',   type: 'number',
                                  restart: false, min: 1000, max: 32000, step: 500 },
                                { group: 'frontend', key: 'ai_system_prompt',        label: '시스템 프롬프트 (직접 모드)',      type: 'textarea',
                                  restart: false, rows: 8, desc: '백엔드 RAG 미사용(직접 모드) 시에만 적용됩니다. 백엔드 RAG 사용 시에는 AI/RAG 탭의 프롬프트가 적용됩니다.' },
                            ]
                        },
                        {
                            title: '에디터',
                            fields: [
                                { group: 'frontend', key: 'editor_enabled',            label: '에디터 활성화',      type: 'toggle',
                                  restart: false, desc: '문서 인라인 편집 기능 활성화 여부' },
                                { group: 'frontend', key: 'editor_auto_save_interval', label: '자동 저장 간격 (ms)', type: 'number',
                                  restart: false, min: 5000, max: 300000, step: 5000,
                                  desc: '에디터 자동 저장 주기 (밀리초). 기본 30000 = 30초' },
                                { group: 'frontend', key: 'editor_create_backup',      label: '저장 시 백업 생성',   type: 'toggle',
                                  restart: false, desc: '파일 저장 전 .bak 백업 파일 생성' },
                            ]
                        }
                    ]
                },
                {
                    tabId: 'tab-menu',
                    tabLabel: '메뉴 관리',
                    sections: []
                }
            ]
        },
        {
            id: 'translator',
            label: 'Translator',
            group: '시스템 설정',
            tabs: [
                {
                    tabId: 'tab-translator',
                    tabLabel: '번역 설정',
                    sections: [
                        {
                            title: '번역 모델',
                            fields: [
                                { group: 'translator', key: 'translation_model',
                                  label: '번역 모델', type: 'text', restart: false,
                                  desc: '번역 전용 Ollama 모델. 비워두면 AI/RAG 탭의 LLM 모델 사용' },
                            ]
                        },
                        {
                            title: '번역 품질',
                            subtabs: [
                                {
                                    subtabId: 'quality-pdf',
                                    subtabLabel: 'PDF (pdf2zh)',
                                    fields: [
                                        { group: 'translator', key: 'custom_prompt',
                                          label: '시스템 프롬프트 (role block)', type: 'textarea', restart: false,
                                          rows: 4,
                                          desc: '--custom-system-prompt 값. 비워두면 BabelDOC 기본 프롬프트 사용. $lang_out 변수 사용 가능',
                                          placeholder: 'You are a professional $lang_out native translator who needs to fluently translate text into $lang_out.' },
                                        { group: 'translator', key: 'disable_rich_text',
                                          label: '리치텍스트 번역 비활성화', type: 'toggle', restart: false,
                                          desc: '<style> 태그 손상 방지. 볼드/이탤릭 서식이 번역에서 제외됨' },
                                        { group: 'translator', key: 'translate_table_text',
                                          label: '테이블 텍스트 번역', type: 'toggle', restart: false,
                                          desc: '표 안의 텍스트도 번역 대상에 포함' },
                                        { group: 'translator', key: 'min_text_length',
                                          label: '최소 텍스트 길이', type: 'number', restart: false,
                                          min: 0, max: 100, step: 1,
                                          desc: '이 글자 수 미만의 텍스트 블록은 번역 건너뜀' },
                                        { group: 'translator', key: 'ocr_workaround',
                                          label: 'OCR 우회', type: 'toggle', restart: false,
                                          desc: '스캔 PDF에서 OCR 처리 활성화' },
                                        { group: 'translator', key: 'enhance_compatibility',
                                          label: '호환성 강화', type: 'toggle', restart: false,
                                          desc: '일부 PDF 뷰어 호환성 문제 해결' },
                                    ]
                                },
                                {
                                    subtabId: 'quality-text',
                                    subtabLabel: '텍스트',
                                    fields: [
                                        { group: 'translator', key: 'text_custom_prompt',
                                          label: '시스템 프롬프트', type: 'textarea', restart: false,
                                          rows: 8,
                                          desc: '텍스트 번역 시 Ollama에 전달되는 system 프롬프트' },
                                        { group: 'translator', key: 'text_font_scale',
                                          label: '폰트 스케일', type: 'number', restart: false,
                                          min: 0.3, max: 1.5, step: 0.05,
                                          desc: '원문 대비 번역 폰트 크기 비율. EN→KR은 0.75 권장 (한글이 영문보다 넓음)' },
                                        { group: 'translator', key: 'text_min_scale',
                                          label: '최소 축소 한도', type: 'number', restart: false,
                                          min: 0.1, max: 1.0, step: 0.05,
                                          desc: '자동 축소 최소 비율. 번역이 박스에 안 맞을 때 이 비율까지 축소 허용' },
                                        { group: 'translator', key: 'text_font_family',
                                          label: '폰트 패밀리', type: 'text', restart: false,
                                          desc: '번역 텍스트에 적용할 CSS 폰트 패밀리 (예: sans-serif, serif, monospace)' },
                                        { group: 'translator', key: 'text_min_text_length',
                                          label: '최소 텍스트 길이', type: 'number', restart: false,
                                          min: 0, max: 100, step: 1,
                                          desc: '이 글자 수 미만의 텍스트 블록은 번역 건너뜀' },
                                    ]
                                },
                                {
                                    subtabId: 'quality-ai-selection',
                                    subtabLabel: 'AI 선택',
                                    fields: [
                                        { group: 'translator', key: 'ai_translate_prompt',
                                          label: '번역 프롬프트', type: 'textarea', restart: false,
                                          rows: 4,
                                          desc: '텍스트 선택 → 번역 시 Ollama에 전달되는 system 프롬프트' },
                                        { group: 'translator', key: 'ai_summarize_prompt',
                                          label: '요약 프롬프트', type: 'textarea', restart: false,
                                          rows: 4,
                                          desc: '텍스트 선택 → 요약 시 Ollama에 전달되는 system 프롬프트' },
                                        { group: 'translator', key: 'ai_selection_timeout',
                                          label: '타임아웃 (초)', type: 'number', restart: false,
                                          min: 5, max: 120, step: 5,
                                          desc: '선택 번역/요약 최대 대기 시간. 짧은 텍스트 대상이므로 30초 권장' },
                                    ]
                                },
                            ]
                        },
                        {
                            title: '동시성 / 성능',
                            fields: [
                                { group: 'translator', key: 'max_concurrent',
                                  label: '동시 번역 수', type: 'number', restart: false,
                                  min: 1, max: 16, step: 1,
                                  desc: 'GPU 부하 제한. 동시에 진행할 수 있는 최대 번역 작업 수' },
                                { group: 'translator', key: 'page_timeout',
                                  label: '페이지 타임아웃 (초)', type: 'number', restart: false,
                                  min: 60, max: 1800, step: 30,
                                  desc: '페이지당 최대 번역 시간. 초과 시 실패 처리' },
                                { group: 'translator', key: 'qps',
                                  label: 'QPS 제한', type: 'number', restart: false,
                                  min: 0, max: 100, step: 1,
                                  desc: 'Ollama 초당 요청 수 제한. 0이면 무제한' },
                            ]
                        },
                    ]
                }
            ]
        }
    ]
};

// ── 메인 렌더러 ───────────────────────────────────────────────────────────────

async function renderAdminSettings() {
    var container = document.getElementById('main-content');
    if (!container) return;

    container.innerHTML = '<div class="admin-settings-page"><div class="admin-settings-loading"><div class="spinner admin-spinner"></div>설정 로드 중...</div></div>';
    if (typeof updateSectionNav === 'function') updateSectionNav();

    var backendUrl = (typeof AUTH_CONFIG !== 'undefined') ? AUTH_CONFIG.backendUrl : 'http://localhost:8000';

    try {
        var r = await fetch(backendUrl + '/api/settings', { credentials: 'include' });
        if (r.status === 401) {
            if (typeof window.handleApiUnauthorized === 'function') window.handleApiUnauthorized();
            return;
        }
        if (r.status === 403) {
            container.innerHTML = '<div class="admin-settings-page"><div class="admin-settings-error"><span>🔒</span><p>관리자 권한이 필요합니다.</p></div></div>';
            return;
        }
        if (!r.ok) throw new Error('HTTP ' + r.status);

        var data = await r.json();
        _renderAdminSettingsUI(container, data.settings);

    } catch (e) {
        container.innerHTML = '<div class="admin-settings-page"><div class="admin-settings-error"><span>⚠</span><p>설정을 불러올 수 없습니다.<br><small>' + _escHtml(e.message) + '</small></p></div></div>';
    }
}

// ── 현재 활성 시스템/탭 상태 ─────────────────────────────────────────────────
var _activeSystemId = null;
var _activeTabId = null;
var _currentSettings = null;

// ── UI 렌더링 ──────────────────────────────────────────────────────────────────

function _renderAdminSettingsUI(container, settings) {
    _currentSettings = settings;
    _activeSystemId = SETTINGS_SCHEMA.systems[0].id;

    var html = '<div class="admin-settings-page">';

    // 헤더
    html += '<div class="page-header">';
    html += '<div class="page-header-info">';
    html += '<h1 class="ph-icon-settings">관리자 설정</h1>';
    html += '</div>';
    html += '<div class="page-header-actions">';
    html += '<button class="admin-btn admin-btn-reset" onclick="_adminReset()">초기화</button>';
    html += '<button class="admin-btn admin-btn-save" id="admin-save-btn" onclick="_adminSave()">저장</button>';
    html += '</div>';
    html += '</div>';

    // 알림 영역
    html += '<div class="admin-settings-notice" id="admin-notice" style="display:none"></div>';

    // 2-column 레이아웃
    html += '<div class="admin-layout">';

    // 사이드바
    html += '<nav class="admin-sidebar">';
    var _lastGroup = '';
    SETTINGS_SCHEMA.systems.forEach(function(sys, idx) {
        if (sys.group && sys.group !== _lastGroup) {
            _lastGroup = sys.group;
            html += '<div class="admin-sidebar-group">' + _escHtml(sys.group) + '</div>';
        }
        html += '<button class="admin-sidebar-btn' + (idx === 0 ? ' active' : '') +
                '" data-system="' + sys.id + '" onclick="_adminSwitchSystem(\'' + sys.id + '\')">' +
                _escHtml(sys.label) + '</button>';
    });
    html += '</nav>';

    // 콘텐츠 영역
    html += '<div class="admin-content" id="admin-content-area"></div>';

    html += '</div>'; // .admin-layout
    html += '</div>'; // .admin-settings-page
    container.innerHTML = html;

    // 첫 번째 시스템 콘텐츠 렌더
    _renderSystemContent(SETTINGS_SCHEMA.systems[0]);

    // 재시작 대기 상태 배너 복원
    if (_pendingRestartItems.length > 0) {
        _showNotice(
            'warn',
            '⚠ 다음 항목이 변경되어 <strong>서버 재시작이 필요</strong>합니다: ' +
            '<code>' + _pendingRestartItems.join(', ') + '</code>'
        );
    }
}

// ── 시스템 전환 ──────────────────────────────────────────────────────────────────

function _adminSwitchSystem(systemId) {
    if (_activeSystemId === systemId) return;

    // 전환 전 현재 DOM 값을 _currentSettings에 반영
    _syncCurrentFields();

    _activeSystemId = systemId;

    // 사이드바 active 토글
    document.querySelectorAll('.admin-sidebar-btn').forEach(function(btn) {
        btn.classList.toggle('active', btn.dataset.system === systemId);
    });

    // 해당 시스템 찾기
    var sys = null;
    SETTINGS_SCHEMA.systems.forEach(function(s) { if (s.id === systemId) sys = s; });
    if (!sys) return;

    _renderSystemContent(sys);
}

// ── 섹션 내 모든 필드 순회 헬퍼 (subtabs 포함) ─────────────────────────────

function _forEachSectionField(section, callback) {
    if (section.subtabs) {
        section.subtabs.forEach(function(st) {
            st.fields.forEach(callback);
        });
    } else if (section.fields) {
        section.fields.forEach(callback);
    }
}

// ── DOM → _currentSettings 동기화 (시스템 전환 전) ───────────────────────────

function _syncCurrentFields() {
    var sys = null;
    SETTINGS_SCHEMA.systems.forEach(function(s) { if (s.id === _activeSystemId) sys = s; });
    if (!sys || sys.custom) return;

    sys.tabs.forEach(function(tab) {
        tab.sections.forEach(function(section) {
            _forEachSectionField(section, function(field) {
                var id = 'as-' + field.group + '-' + field.key;
                var el = document.getElementById(id);
                if (!el) return;

                if (!_currentSettings[field.group]) _currentSettings[field.group] = {};
                var val;
                if (field.type === 'toggle') {
                    val = el.checked;
                } else if (field.type === 'number') {
                    var parsed = parseFloat(el.value);
                    val = isNaN(parsed) ? null : parsed;
                } else if (field.type === 'textarea' && field.fromStr) {
                    val = field.fromStr(el.value);
                } else {
                    val = el.value.trim() || null;
                }
                _currentSettings[field.group][field.key] = val;
            });
        });
    });
}

// ── 시스템 콘텐츠 렌더 ──────────────────────────────────────────────────────────

function _renderSystemContent(sys) {
    var area = document.getElementById('admin-content-area');
    if (!area) return;

    // 커스텀 패널
    if (sys.custom) {
        if (sys.id === 'users') { _renderUsersPanel(area); return; }
        if (sys.id === 'dashboard') { _renderDashboardPanel(area); return; }
        area.innerHTML = '';
        return;
    }

    var firstTab = sys.tabs[0];
    _activeTabId = firstTab ? firstTab.tabId : null;
    var html = '';

    // 탭 바: 2개 이상일 때만 표시
    if (sys.tabs.length >= 2) {
        html += '<div class="admin-tabs">';
        sys.tabs.forEach(function(tab, idx) {
            html += '<button class="admin-tab-btn' + (idx === 0 ? ' active' : '') +
                    '" data-tab="' + tab.tabId + '" onclick="_adminSwitchTab(\'' + tab.tabId + '\')">' +
                    _escHtml(tab.tabLabel) + '</button>';
        });
        html += '</div>';
    }

    // 탭 패널
    sys.tabs.forEach(function(tab, idx) {
        html += '<div class="admin-tab-panel' + (idx === 0 ? ' active' : '') + '" id="' + tab.tabId + '">';
        tab.sections.forEach(function(section) {
            html += '<div class="admin-section">';
            html += '<h3 class="admin-section-title">' + _escHtml(section.title) + '</h3>';

            if (section.subtabs) {
                // 서브탭 렌더링
                html += '<div class="admin-subtabs">';
                section.subtabs.forEach(function(st, stIdx) {
                    html += '<button class="admin-subtab-btn' + (stIdx === 0 ? ' active' : '') +
                            '" data-subtab="' + st.subtabId + '" onclick="_adminSwitchSubtab(\'' + st.subtabId + '\',this)">' +
                            _escHtml(st.subtabLabel) + '</button>';
                });
                html += '</div>';
                section.subtabs.forEach(function(st, stIdx) {
                    html += '<div class="admin-subtab-panel' + (stIdx === 0 ? ' active' : '') + '" id="' + st.subtabId + '">';
                    html += '<div class="admin-fields">';
                    st.fields.forEach(function(field) {
                        html += _renderField(field, _currentSettings);
                    });
                    html += '</div>';
                    html += '</div>';
                });
            } else {
                html += '<div class="admin-fields">';
                section.fields.forEach(function(field) {
                    html += _renderField(field, _currentSettings);
                });
                html += '</div>';
            }

            html += '</div>';
        });
        html += '</div>';
    });

    area.innerHTML = html;

    // 메뉴 관리 탭 커스텀 렌더링
    if (sys.id === 'explorer') _renderMenuTab();
}

// ── 필드 렌더링 ───────────────────────────────────────────────────────────────

function _renderField(field, settings) {
    var val = (settings[field.group] || {})[field.key];
    var id = 'as-' + field.group + '-' + field.key;

    var restartBadge = field.restart
        ? '<span class="admin-restart-badge" title="변경 후 서버 재시작 필요">재시작 필요</span>'
        : '';

    var desc = field.desc
        ? '<div class="admin-field-desc">' + _escHtml(field.desc) + '</div>'
        : '';

    var control = _renderControl(field, val, id);

    return '<div class="admin-field admin-field-' + field.type + '">' +
        '<div class="admin-field-header">' +
        '<label class="admin-field-label" for="' + id + '">' + _escHtml(field.label) + '</label>' +
        restartBadge +
        '</div>' +
        desc +
        '<div class="admin-field-control">' + control + '</div>' +
        '</div>';
}

function _renderControl(field, val, id) {
    switch (field.type) {
        case 'toggle':
            return '<label class="admin-toggle">' +
                '<input type="checkbox" id="' + id + '"' + (val ? ' checked' : '') + '>' +
                '<span class="admin-toggle-slider"></span>' +
                '</label>';

        case 'select': {
            var opts = (field.options || []).map(function(opt) {
                var sel = (String(val) === String(opt[0])) ? ' selected' : '';
                return '<option value="' + _escHtml(opt[0]) + '"' + sel + '>' + _escHtml(opt[1]) + '</option>';
            }).join('');
            return '<select class="admin-select" id="' + id + '">' + opts + '</select>';
        }

        case 'number': {
            var attrs = ' value="' + (val !== undefined && val !== null ? val : '') + '"';
            if (field.min !== undefined) attrs += ' min="' + field.min + '"';
            if (field.max !== undefined) attrs += ' max="' + field.max + '"';
            if (field.step !== undefined) attrs += ' step="' + field.step + '"';
            return '<input type="number" class="admin-input admin-number" id="' + id + '"' + attrs + '>';
        }

        case 'textarea': {
            var displayVal = val;
            if (field.toStr && val !== undefined && val !== null) {
                displayVal = field.toStr(val);
            }
            var rows = field.rows || 3;
            var ph = field.placeholder ? ' placeholder="' + _escHtml(field.placeholder) + '"' : '';
            return '<textarea class="admin-textarea" id="' + id + '" rows="' + rows + '"' + ph + '>' +
                _escHtml(displayVal !== undefined && displayVal !== null ? String(displayVal) : '') +
                '</textarea>';
        }

        default: // text
            return '<input type="text" class="admin-input" id="' + id + '" value="' +
                _escHtml(val !== undefined && val !== null ? String(val) : '') + '">';
    }
}

// ── 탭 전환 ───────────────────────────────────────────────────────────────────

function _adminSwitchTab(tabId) {
    _activeTabId = tabId;
    var area = document.getElementById('admin-content-area');
    if (!area) return;
    area.querySelectorAll('.admin-tab-btn').forEach(function(btn) {
        btn.classList.toggle('active', btn.dataset.tab === tabId);
    });
    area.querySelectorAll('.admin-tab-panel').forEach(function(panel) {
        panel.classList.toggle('active', panel.id === tabId);
    });
}

// ── 서브탭 전환 ──────────────────────────────────────────────────────────────

function _adminSwitchSubtab(subtabId, btn) {
    var section = btn.closest('.admin-section');
    if (!section) return;
    section.querySelectorAll('.admin-subtab-btn').forEach(function(b) {
        b.classList.toggle('active', b.dataset.subtab === subtabId);
    });
    section.querySelectorAll('.admin-subtab-panel').forEach(function(panel) {
        panel.classList.toggle('active', panel.id === subtabId);
    });
}

// ── 설정값 수집 ───────────────────────────────────────────────────────────────

function _collectSettings() {
    // 현재 DOM에 있는 필드를 먼저 _currentSettings에 반영
    _syncCurrentFields();

    // _currentSettings에서 스키마에 정의된 모든 필드를 수집
    var result = {};
    SETTINGS_SCHEMA.systems.forEach(function(sys) {
        if (sys.custom || !sys.tabs) return;
        sys.tabs.forEach(function(tab) {
            tab.sections.forEach(function(section) {
                _forEachSectionField(section, function(field) {
                    if (!result[field.group]) result[field.group] = {};
                    var groupData = _currentSettings[field.group];
                    if (groupData && field.key in groupData) {
                        result[field.group][field.key] = groupData[field.key];
                    }
                });
            });
        });
    });
    return result;
}

// ── 저장 ─────────────────────────────────────────────────────────────────────

async function _adminSave() {
    var saveBtn = document.getElementById('admin-save-btn');
    if (saveBtn) { saveBtn.disabled = true; saveBtn.textContent = '저장 중...'; }

    _hideNotice();

    var settings = _collectSettings();
    var backendUrl = (typeof AUTH_CONFIG !== 'undefined') ? AUTH_CONFIG.backendUrl : 'http://localhost:8000';

    try {
        var r = await fetch(backendUrl + '/api/settings', {
            method: 'POST',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(settings)
        });

        if (r.status === 401) {
            if (typeof window.handleApiUnauthorized === 'function') window.handleApiUnauthorized();
            return;
        }
        if (!r.ok) throw new Error('HTTP ' + r.status);

        var data = await r.json();

        if (data.restart_needed && data.restart_needed.length > 0) {
            // 기존 목록에 중복 없이 누적
            data.restart_needed.forEach(function(item) {
                if (_pendingRestartItems.indexOf(item) === -1) _pendingRestartItems.push(item);
            });
            _showNotice(
                'warn',
                '⚠ 저장되었습니다. 다음 항목은 <strong>서버 재시작 후</strong> 적용됩니다: ' +
                '<code>' + _pendingRestartItems.join(', ') + '</code>'
            );
        } else {
            _showNotice('ok', '✓ 설정이 저장되었으며 즉시 적용되었습니다.');
        }

    } catch (e) {
        _showNotice('error', '✗ 저장 실패: ' + _escHtml(e.message));
    } finally {
        if (saveBtn) { saveBtn.disabled = false; saveBtn.textContent = '저장'; }
    }
}

// ── 초기화 ────────────────────────────────────────────────────────────────────

async function _adminReset() {
    if (!confirm('모든 설정을 기본값으로 초기화하시겠습니까?\n저장된 settings.json이 삭제됩니다.')) return;

    var backendUrl = (typeof AUTH_CONFIG !== 'undefined') ? AUTH_CONFIG.backendUrl : 'http://localhost:8000';

    try {
        var r = await fetch(backendUrl + '/api/settings/reset', {
            method: 'POST',
            credentials: 'include'
        });
        if (r.status === 401) {
            if (typeof window.handleApiUnauthorized === 'function') window.handleApiUnauthorized();
            return;
        }
        if (!r.ok) throw new Error('HTTP ' + r.status);
        // 초기화 → 재시작 대기 상태도 클리어
        _pendingRestartItems = [];
        renderAdminSettings();
    } catch (e) {
        alert('초기화 실패: ' + e.message);
    }
}

// ── 알림 유틸 ─────────────────────────────────────────────────────────────────

function _showNotice(type, html) {
    var el = document.getElementById('admin-notice');
    if (!el) return;
    el.className = 'admin-settings-notice notice-' + type;
    el.innerHTML = html;
    el.style.display = 'block';
    if (type === 'ok') {
        setTimeout(function() { if (el) el.style.display = 'none'; }, 5000);
    }
}

function _hideNotice() {
    var el = document.getElementById('admin-notice');
    if (el) el.style.display = 'none';
}

function _escHtml(s) {
    return String(s)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

// ══════════════════════════════════════════════════════════════════════════════
// ── 메뉴 관리 탭 ─────────────────────────────────────────────────────────────
// ══════════════════════════════════════════════════════════════════════════════

var _menuEditorData = null;

function _renderMenuTab() {
    var panel = document.getElementById('tab-menu');
    if (!panel) return;

    panel.innerHTML =
        '<div class="admin-section">' +
            '<h3 class="admin-section-title">\uBA54\uB274 \uAD6C\uC870 \uD3B8\uC9D1</h3>' +
            '<div class="menu-editor">' +
                '<div class="menu-editor-loading"><div class="spinner admin-spinner"></div> \uBA54\uB274 \uB85C\uB4DC \uC911...</div>' +
            '</div>' +
        '</div>';

    _menuFetchData();
}

async function _menuFetchData() {
    var backendUrl = (typeof AUTH_CONFIG !== 'undefined') ? AUTH_CONFIG.backendUrl : 'http://localhost:8000';
    try {
        var r = await fetch(backendUrl + '/api/menu', { credentials: 'include' });
        if (r.status === 401) {
            if (typeof window.handleApiUnauthorized === 'function') window.handleApiUnauthorized();
            return;
        }
        if (!r.ok) throw new Error('HTTP ' + r.status);
        var data = await r.json();
        _menuEditorData = data.menu || [];
        _menuRenderEditor();
    } catch (e) {
        var editor = document.querySelector('.menu-editor');
        if (editor) {
            editor.innerHTML = '<div class="menu-editor-error">\uBA54\uB274\uB97C \uBD88\uB7EC\uC62C \uC218 \uC5C6\uC2B5\uB2C8\uB2E4: ' + _escHtml(e.message) + '</div>';
        }
    }
}

// ── 트리 렌더링 ───────────────────────────────────────────────────────────────

function _menuRenderEditor() {
    var editor = document.querySelector('.menu-editor');
    if (!editor) return;

    var html = '<div class="menu-toolbar">';
    html += '<button class="admin-btn admin-btn-save" onclick="_menuAddTopLevel()" style="padding:6px 14px;font-size:12px;">+ \uCD5C\uC0C1\uC704 \uD56D\uBAA9 \uCD94\uAC00</button>';
    html += '</div>';
    html += '<div class="menu-tree">';
    if (_menuEditorData && _menuEditorData.length > 0) {
        html += _menuRenderNodes(_menuEditorData, 0, []);
    } else {
        html += '<div class="menu-tree-empty">\uBA54\uB274 \uD56D\uBAA9\uC774 \uC5C6\uC2B5\uB2C8\uB2E4. \uC704 \uBC84\uD2BC\uC73C\uB85C \uCD94\uAC00\uD558\uC138\uC694.</div>';
    }
    html += '</div>';
    html += '<div class="menu-editor-actions">';
    html += '<button class="admin-btn admin-btn-save" onclick="_menuSave()">\uC800\uC7A5</button>';
    html += '</div>';
    editor.innerHTML = html;
}

function _menuRenderNodes(nodes, depth, pathPrefix) {
    var html = '';
    for (var i = 0; i < nodes.length; i++) {
        html += _menuRenderNode(nodes[i], depth, i, nodes.length, pathPrefix.concat([i]));
    }
    return html;
}

function _menuRenderNode(node, depth, index, siblingCount, path) {
    var hasChildren = node.children && node.children.length > 0;
    var isFolder = hasChildren || !node.url;
    var indent = depth * 20;
    var pathStr = path.join(',');

    var html = '<div class="menu-node" data-depth="' + depth + '" data-path="' + pathStr + '">';
    html += '<div class="menu-node-row" style="padding-left:' + (indent + 8) + 'px">';

    if (hasChildren) {
        html += '<span class="menu-node-toggle" onclick="_menuToggleChildren(this)">&#9660;</span>';
    } else {
        html += '<span class="menu-node-toggle-placeholder"></span>';
    }

    html += '<span class="menu-node-icon">' + (isFolder ? '\uD83D\uDCC1' : '\uD83D\uDCC4') + '</span>';
    html += '<span class="menu-node-label">' + _escHtml(node.label || '') + '</span>';
    html += '<span class="menu-node-url">' + (node.url ? _escHtml(node.url) : '\u2014') + '</span>';

    html += '<div class="menu-node-actions">';
    html += '<button class="menu-btn" title="\uC704\uB85C" onclick="_menuMoveByPath(\'' + pathStr + '\',-1)"' + (index === 0 ? ' disabled' : '') + '>&#9650;</button>';
    html += '<button class="menu-btn" title="\uC544\uB798\uB85C" onclick="_menuMoveByPath(\'' + pathStr + '\',1)"' + (index === siblingCount - 1 ? ' disabled' : '') + '>&#9660;</button>';
    html += '<button class="menu-btn" title="\uD558\uC704 \uCD94\uAC00" onclick="_menuAddChildByPath(\'' + pathStr + '\')">+</button>';
    html += '<button class="menu-btn" title="\uD3B8\uC9D1" onclick="_menuEditByPath(\'' + pathStr + '\')">\u270E</button>';
    html += '<button class="menu-btn menu-btn-danger" title="\uC0AD\uC81C" onclick="_menuDeleteByPath(\'' + pathStr + '\')">\u2715</button>';
    html += '</div>';
    html += '</div>';

    if (hasChildren) {
        html += '<div class="menu-node-children">';
        html += _menuRenderNodes(node.children, depth + 1, path);
        html += '</div>';
    }

    html += '</div>';
    return html;
}

// ── 경로 헬퍼 ─────────────────────────────────────────────────────────────────

function _menuParsePath(pathStr) {
    return pathStr.split(',').map(function(s) { return parseInt(s, 10); });
}

function _menuNodeByPath(path) {
    var list = _menuEditorData;
    var node = null;
    for (var i = 0; i < path.length; i++) {
        node = list[path[i]];
        if (!node) return null;
        if (i < path.length - 1) {
            list = node.children || [];
        }
    }
    return { node: node, parentList: _menuParentList(path), index: path[path.length - 1] };
}

function _menuParentList(path) {
    if (path.length <= 1) return _menuEditorData;
    var list = _menuEditorData;
    for (var i = 0; i < path.length - 1; i++) {
        var n = list[path[i]];
        if (!n) return list;
        list = n.children || [];
    }
    return list;
}

// ── 토글 ──────────────────────────────────────────────────────────────────────

function _menuToggleChildren(toggleEl) {
    var nodeEl = toggleEl.closest('.menu-node');
    var childrenEl = nodeEl.querySelector(':scope > .menu-node-children');
    if (!childrenEl) return;
    var collapsed = childrenEl.style.display === 'none';
    childrenEl.style.display = collapsed ? '' : 'none';
    toggleEl.innerHTML = collapsed ? '&#9660;' : '&#9654;';
}

// ── 추가 ──────────────────────────────────────────────────────────────────────

function _menuAddTopLevel() {
    if (!_menuEditorData) _menuEditorData = [];
    _menuEditorData.push({ label: '\uC0C8 \uD56D\uBAA9' });
    _menuRenderEditor();
    _menuEditByPath(String(_menuEditorData.length - 1));
}

function _menuAddChildByPath(pathStr) {
    var path = _menuParsePath(pathStr);
    var ctx = _menuNodeByPath(path);
    if (!ctx || !ctx.node) return;
    if (!ctx.node.children) ctx.node.children = [];
    ctx.node.children.push({ label: '\uC0C8 \uD56D\uBAA9' });
    _menuRenderEditor();
    _menuEditByPath(path.concat([ctx.node.children.length - 1]).join(','));
}

// ── 삭제 ──────────────────────────────────────────────────────────────────────

function _menuCollectUrls(node) {
    var urls = [];
    if (node.url) urls.push(node.url);
    if (node.children) {
        node.children.forEach(function(child) {
            urls = urls.concat(_menuCollectUrls(child));
        });
    }
    return urls;
}

function _menuDeleteByPath(pathStr) {
    var path = _menuParsePath(pathStr);
    var ctx = _menuNodeByPath(path);
    if (!ctx || !ctx.node) return;

    var linkedUrls = _menuCollectUrls(ctx.node);
    var hasChildren = ctx.node.children && ctx.node.children.length > 0;

    var msg = '"' + ctx.node.label + '"';
    if (hasChildren) {
        msg += ' \uD56D\uBAA9\uACFC \uD558\uC704 ' + ctx.node.children.length + '\uAC1C \uD56D\uBAA9\uC744 \uBAA8\uB450 \uC0AD\uC81C\uD569\uB2C8\uB2E4.';
    } else {
        msg += ' \uD56D\uBAA9\uC744 \uC0AD\uC81C\uD569\uB2C8\uB2E4.';
    }

    if (linkedUrls.length > 0) {
        msg += '\n\n\u26A0 \uC5F0\uACB0\uB41C \uBB38\uC11C ' + linkedUrls.length + '\uAC1C\uAC00 \uC788\uC2B5\uB2C8\uB2E4:';
        linkedUrls.slice(0, 5).forEach(function(u) { msg += '\n  \u2022 ' + u; });
        if (linkedUrls.length > 5) msg += '\n  \u2026 \uC678 ' + (linkedUrls.length - 5) + '\uAC1C';
        msg += '\n\n\uC0AD\uC81C\uD558\uBA74 \uBA54\uB274\uC5D0\uC11C \uC811\uADFC\uD560 \uC218 \uC5C6\uAC8C \uB429\uB2C8\uB2E4.\n(\uB514\uC2A4\uD06C\uC758 \uD30C\uC77C\uC740 \uC0AD\uC81C\uB418\uC9C0 \uC54A\uC2B5\uB2C8\uB2E4)';
    }

    msg += '\n\n\uC0AD\uC81C\uD558\uC2DC\uACA0\uC2B5\uB2C8\uAE4C?';
    if (!confirm(msg)) return;

    ctx.parentList.splice(ctx.index, 1);
    _menuRenderEditor();
}

// ── 이동 ──────────────────────────────────────────────────────────────────────

function _menuMoveByPath(pathStr, direction) {
    var path = _menuParsePath(pathStr);
    var ctx = _menuNodeByPath(path);
    if (!ctx) return;

    var newIndex = ctx.index + direction;
    if (newIndex < 0 || newIndex >= ctx.parentList.length) return;

    var temp = ctx.parentList[ctx.index];
    ctx.parentList[ctx.index] = ctx.parentList[newIndex];
    ctx.parentList[newIndex] = temp;
    _menuRenderEditor();
}

// ── 인라인 편집 ───────────────────────────────────────────────────────────────

function _menuEditByPath(pathStr) {
    var path = _menuParsePath(pathStr);
    var ctx = _menuNodeByPath(path);
    if (!ctx || !ctx.node) return;

    var nodeEl = document.querySelector('.menu-node[data-path="' + pathStr + '"]');
    if (!nodeEl) return;
    var rowEl = nodeEl.querySelector(':scope > .menu-node-row');
    if (!rowEl) return;

    var editHtml =
        '<div class="menu-node-edit" style="padding-left:' + rowEl.style.paddingLeft + '">' +
            '<input class="admin-input menu-edit-label" placeholder="\uC774\uB984" value="' + _escHtml(ctx.node.label || '') + '">' +
            '<input class="admin-input menu-edit-url" placeholder="URL (\uBE44\uC6CC\uB450\uBA74 \uD3F4\uB354)" value="' + _escHtml(ctx.node.url || '') + '">' +
            '<button class="menu-btn menu-btn-ok" onclick="_menuEditConfirm(\'' + pathStr + '\',this)">\uD655\uC778</button>' +
            '<button class="menu-btn" onclick="_menuEditCancel()">\uCDE8\uC18C</button>' +
        '</div>';

    rowEl.style.display = 'none';
    rowEl.insertAdjacentHTML('afterend', editHtml);

    var labelInput = nodeEl.querySelector('.menu-edit-label');
    if (labelInput) { labelInput.focus(); labelInput.select(); }

    var editDiv = nodeEl.querySelector('.menu-node-edit');
    if (editDiv) {
        editDiv.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') _menuEditConfirm(pathStr, editDiv.querySelector('.menu-btn-ok'));
            else if (e.key === 'Escape') _menuEditCancel();
        });
    }
}

function _menuEditConfirm(pathStr, btnEl) {
    var path = _menuParsePath(pathStr);
    var ctx = _menuNodeByPath(path);
    if (!ctx || !ctx.node) return;

    var editDiv = btnEl.closest('.menu-node-edit');
    if (!editDiv) return;

    var label = editDiv.querySelector('.menu-edit-label').value.trim();
    var url = editDiv.querySelector('.menu-edit-url').value.trim();

    if (!label) { alert('\uC774\uB984\uC740 \uD544\uC218\uC785\uB2C8\uB2E4.'); return; }

    ctx.node.label = label;
    if (url) { ctx.node.url = url; } else { delete ctx.node.url; }
    _menuRenderEditor();
}

function _menuEditCancel() {
    _menuRenderEditor();
}

// ── 메뉴 저장 ─────────────────────────────────────────────────────────────────

async function _menuSave() {
    var saveBtn = document.querySelector('.menu-editor-actions .admin-btn-save');
    if (saveBtn) { saveBtn.disabled = true; saveBtn.textContent = '\uC800\uC7A5 \uC911...'; }

    var backendUrl = (typeof AUTH_CONFIG !== 'undefined') ? AUTH_CONFIG.backendUrl : 'http://localhost:8000';

    try {
        var r = await fetch(backendUrl + '/api/menu', {
            method: 'POST',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(_menuEditorData)
        });

        if (r.status === 401) {
            if (typeof window.handleApiUnauthorized === 'function') window.handleApiUnauthorized();
            return;
        }
        if (!r.ok) throw new Error('HTTP ' + r.status);

        _showNotice('ok', '\u2713 \uBA54\uB274\uAC00 \uC800\uC7A5\uB418\uC5C8\uC2B5\uB2C8\uB2E4.');

        // 좌측 패널 갱신
        if (typeof loadMenuData === 'function') loadMenuData();

    } catch (e) {
        _showNotice('error', '\u2717 \uBA54\uB274 \uC800\uC7A5 \uC2E4\uD328: ' + _escHtml(e.message));
    } finally {
        if (saveBtn) { saveBtn.disabled = false; saveBtn.textContent = '\uC800\uC7A5'; }
    }
}

// ══════════════════════════════════════════════════════════════════════════════
//  계정 관리 패널
// ══════════════════════════════════════════════════════════════════════════════

function _renderUsersPanel(area) {
    var backendUrl = (typeof AUTH_CONFIG !== 'undefined') ? AUTH_CONFIG.backendUrl : 'http://localhost:8000';

    area.innerHTML =
        '<div class="admin-section">' +
            '<h3 class="admin-section-title">사용자 목록</h3>' +
            '<table class="admin-users-table">' +
                '<thead><tr><th>ID</th><th>Username</th><th>Role</th><th>Created</th><th>Actions</th></tr></thead>' +
                '<tbody id="admin-users-tbody"></tbody>' +
            '</table>' +
        '</div>' +
        '<div class="admin-section">' +
            '<h3 class="admin-section-title">사용자 추가</h3>' +
            '<div class="admin-users-add-form">' +
                '<input type="text" class="admin-input" id="admin-new-user-name" placeholder="Username">' +
                '<input type="password" class="admin-input" id="admin-new-user-pw" placeholder="Password">' +
                '<select class="admin-select" id="admin-new-user-role">' +
                    '<option value="viewer">viewer</option>' +
                    '<option value="editor">editor</option>' +
                    '<option value="admin">admin</option>' +
                '</select>' +
                '<button class="admin-btn admin-btn-save" id="admin-add-user-btn">추가</button>' +
            '</div>' +
        '</div>';

    _loadUsersTable(backendUrl);

    document.getElementById('admin-add-user-btn').addEventListener('click', function() {
        _addUser(backendUrl);
    });
    document.getElementById('admin-new-user-pw').addEventListener('keydown', function(e) {
        if (e.key === 'Enter') _addUser(backendUrl);
    });
}

async function _loadUsersTable(backendUrl) {
    var tbody = document.getElementById('admin-users-tbody');
    if (!tbody) return;

    try {
        var r = await fetch(backendUrl + '/api/auth/users', { credentials: 'include' });
        if (!r.ok) throw new Error('HTTP ' + r.status);
        var data = await r.json();

        tbody.innerHTML = '';
        data.users.forEach(function(u) {
            var tr = document.createElement('tr');
            tr.innerHTML =
                '<td>' + u.id + '</td>' +
                '<td>' + _escHtml(u.username) + '</td>' +
                '<td><span class="admin-role-badge role-' + u.role + '">' + u.role + '</span></td>' +
                '<td>' + (u.created_at || '-') + '</td>' +
                '<td class="admin-users-actions">' +
                    '<button class="admin-btn-sm" data-action="edit" data-id="' + u.id + '" data-name="' + _escHtml(u.username) + '" data-role="' + u.role + '">Edit</button>' +
                    '<button class="admin-btn-sm admin-btn-danger" data-action="delete" data-id="' + u.id + '" data-name="' + _escHtml(u.username) + '">Delete</button>' +
                '</td>';
            tbody.appendChild(tr);
        });

        tbody.querySelectorAll('[data-action="edit"]').forEach(function(btn) {
            btn.addEventListener('click', function() {
                _editUserInline(backendUrl, this.dataset.id, this.dataset.name, this.dataset.role);
            });
        });
        tbody.querySelectorAll('[data-action="delete"]').forEach(function(btn) {
            btn.addEventListener('click', function() {
                _deleteUser(backendUrl, this.dataset.id, this.dataset.name);
            });
        });
    } catch (e) {
        tbody.innerHTML = '<tr><td colspan="5">Failed to load users</td></tr>';
    }
}

async function _addUser(backendUrl) {
    var nameEl = document.getElementById('admin-new-user-name');
    var pwEl = document.getElementById('admin-new-user-pw');
    var roleEl = document.getElementById('admin-new-user-role');
    var username = nameEl.value.trim();
    var password = pwEl.value;
    var role = roleEl.value;

    if (!username || !password) {
        _showNotice('error', 'Username and password are required.');
        return;
    }

    try {
        var r = await fetch(backendUrl + '/api/auth/users', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ username: username, password: password, role: role })
        });
        if (r.ok) {
            nameEl.value = '';
            pwEl.value = '';
            _loadUsersTable(backendUrl);
            _showNotice('ok', '✓ 사용자가 추가되었습니다: ' + _escHtml(username));
        } else {
            var err = await r.json();
            _showNotice('error', '✗ ' + (err.detail || 'Failed to add user'));
        }
    } catch (e) {
        _showNotice('error', '✗ 서버 오류');
    }
}

function _editUserInline(backendUrl, userId, currentName, currentRole) {
    var existing = document.getElementById('admin-edit-user-overlay');
    if (existing) existing.remove();

    var overlay = document.createElement('div');
    overlay.id = 'admin-edit-user-overlay';
    overlay.className = 'admin-modal-overlay';
    overlay.innerHTML =
        '<div class="admin-modal">' +
            '<h3>Edit User: ' + _escHtml(currentName) + '</h3>' +
            '<div class="admin-field" style="margin-bottom:12px">' +
                '<label class="admin-field-label">New Password <span style="font-weight:normal;opacity:.6">(leave empty to keep)</span></label>' +
                '<input type="password" class="admin-input" id="admin-edit-pw" autocomplete="new-password">' +
            '</div>' +
            '<div class="admin-field" style="margin-bottom:16px">' +
                '<label class="admin-field-label">Role</label>' +
                '<select class="admin-select" id="admin-edit-role">' +
                    '<option value="viewer"' + (currentRole === 'viewer' ? ' selected' : '') + '>viewer</option>' +
                    '<option value="editor"' + (currentRole === 'editor' ? ' selected' : '') + '>editor</option>' +
                    '<option value="admin"' + (currentRole === 'admin' ? ' selected' : '') + '>admin</option>' +
                '</select>' +
            '</div>' +
            '<div style="display:flex;gap:8px;justify-content:flex-end">' +
                '<button class="admin-btn admin-btn-reset" id="admin-edit-cancel">Cancel</button>' +
                '<button class="admin-btn admin-btn-save" id="admin-edit-save">Save</button>' +
            '</div>' +
        '</div>';

    document.body.appendChild(overlay);

    function close() { overlay.remove(); }
    document.getElementById('admin-edit-cancel').addEventListener('click', close);
    overlay.addEventListener('click', function(e) { if (e.target === overlay) close(); });

    document.getElementById('admin-edit-save').addEventListener('click', function() {
        var newPw = document.getElementById('admin-edit-pw').value;
        var newRole = document.getElementById('admin-edit-role').value;
        var body = {};
        if (newPw) body.password = newPw;
        if (newRole !== currentRole) body.role = newRole;
        if (Object.keys(body).length === 0) { close(); return; }

        fetch(backendUrl + '/api/auth/users/' + userId, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify(body)
        }).then(function(r) {
            if (r.ok) {
                _loadUsersTable(backendUrl);
                _showNotice('ok', '✓ 사용자가 수정되었습니다.');
                close();
            } else {
                r.json().then(function(err) { _showNotice('error', '✗ ' + (err.detail || 'Failed')); });
            }
        }).catch(function() { _showNotice('error', '✗ 서버 오류'); });
    });
}

function _deleteUser(backendUrl, userId, name) {
    if (!confirm('"' + name + '" 사용자를 삭제하시겠습니까?')) return;

    fetch(backendUrl + '/api/auth/users/' + userId, {
        method: 'DELETE',
        credentials: 'include'
    }).then(function(r) {
        if (r.ok) {
            _loadUsersTable(backendUrl);
            _showNotice('ok', '✓ 사용자가 삭제되었습니다.');
        } else {
            r.json().then(function(err) { _showNotice('error', '✗ ' + (err.detail || 'Failed')); });
        }
    }).catch(function() { _showNotice('error', '✗ 서버 오류'); });
}

// ══════════════════════════════════════════════════════════════════════════════
//  대시보드 패널
// ══════════════════════════════════════════════════════════════════════════════

function _renderDashboardPanel(area) {
    if (typeof renderAnalyticsDashboard === 'function') {
        renderAnalyticsDashboard(area);
    } else {
        area.innerHTML = '<div class="admin-section"><p>analytics.js가 로드되지 않았습니다.</p></div>';
    }
}
