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

// ── 설정 스키마 (서브시스템별 재구성 — Plan-32) ──────────────────────────────
var SETTINGS_SCHEMA = {
    systems: [
        // ── 운영 ──
        {
            id: 'users',
            label: '계정 관리',
            custom: true,
            group: '운영',
        },
        {
            id: 'dashboard',
            label: '대시보드',
            custom: true,
            group: '운영',
        },
        // ── 설정 ──
        {
            id: 'common',
            label: '공통',
            group: '설정',
            tabs: [
                {
                    tabId: 'tab-common',
                    tabLabel: '공통',
                    sections: [
                        {
                            title: 'AI 연결',
                            fields: [
                                { group: 'ai', key: 'ollama_url', label: 'Ollama URL', type: 'text', restart: true,
                                  placeholder: 'http://localhost:11434',
                                  desc: 'Ollama 서버 주소. Docker 환경에서는 .env 파일로 관리됩니다.' },
                                { group: 'ai', key: 'ollama_model', label: '플랫폼 AI 모델', type: 'text', restart: true,
                                  placeholder: 'gemma3:4b',
                                  desc: '플랫폼 전체에서 사용하는 기본 AI 모델. 각 서브시스템에서 전용 모델을 지정하지 않으면 이 모델이 사용됩니다.' },
                            ]
                        },
                        {
                            title: 'AI 동시성 제어 (LLM Gateway)',
                            desc: '여러 사용자 동시 AI 호출 시 Ollama 부하를 제한합니다. 관리자 대시보드의 "AI 동시성 상태" 에서 현재 수치 확인 가능.',
                            fields: [
                                { group: 'llm_gateway', key: 'enabled', label: 'Gateway 활성화', type: 'toggle',
                                  restart: false,
                                  desc: '비활성화 시 Semaphore 우회 (shadow 단계·롤백용). 즉시 반영.' },
                                { group: 'llm_gateway', key: 'max_concurrent', label: '동시 LLM 호출 최대', type: 'number',
                                  restart: true, min: 1, max: 32, step: 1,
                                  desc: '채팅·요약·분류·번역 LLM 호출 공유 상한 (스트림 제외). 기본 8. 변경 시 재시작 필요 (활성 Semaphore 교체로 대기 요청 교착 방지).' },
                                { group: 'llm_gateway', key: 'stream_slots', label: '스트림 전용 슬롯', type: 'number',
                                  restart: true, min: 1, max: 16, step: 1,
                                  desc: 'Q&A 스트림 전용 슬롯 수. 긴 스트림이 짧은 채팅을 굶지 않도록 분리. 기본 3. 변경 시 재시작 필요.' },
                                { group: 'llm_gateway', key: 'max_queue', label: '대기열 최대 요청 수', type: 'number',
                                  restart: true, min: 4, max: 256, step: 1,
                                  desc: '대기 요청 한도 초과 시 사용자에게 HTTP 429(자동 재시도 토스트). 기본 32. 변경 시 재시작 필요.' },
                            ]
                        },
                        {
                            title: '보안',
                            fields: [
                                { group: 'security', key: 'login_required', label: '열람 로그인 필수', type: 'toggle',
                                  restart: true, desc: '활성화 시 비로그인 사용자의 접근 차단. 변경 후 서버 재시작 필요' },
                                { group: 'session', key: 'session_expiry_hours', label: '로그인 세션 만료 (시간)', type: 'number',
                                  restart: true, min: 1, max: 720, step: 1,
                                  desc: '로그인 유지 시간. 이 시간이 지나면 자동 로그아웃 (재시작 필요)' },
                            ]
                        },
                    ]
                }
            ]
        },
        // ── Explorer ──
        {
            id: 'explorer',
            label: 'Explorer',
            group: '설정',
            tabs: [
                {
                    tabId: 'tab-explorer-content',
                    tabLabel: '콘텐츠',
                    sections: [
                        {
                            title: '표시',
                            fields: [
                                { group: 'frontend', key: 'display_site_title',  label: '사이트 타이틀', type: 'text',
                                  restart: false, desc: 'Explorer 헤더 및 브라우저 탭에 표시되는 사이트 이름' },
                                { group: 'frontend', key: 'display_table_style', label: '테이블 스타일', type: 'select',
                                  options: [['bordered','Bordered — 테두리형 (기본)'], ['simple','Simple — 심플'], ['minimal','Minimal — 최소']],
                                  restart: false, desc: '문서 내 테이블의 표시 스타일' },
                            ]
                        },
                        {
                            title: '업로드',
                            fields: [
                                { group: 'frontend', key: 'upload_enabled',           label: '업로드 기능 활성화',             type: 'toggle',
                                  restart: false, desc: 'Editor 이상 권한 사용자의 파일 업로드 UI 표시 여부' },
                                { group: 'frontend', key: 'upload_max_file_size_mb',  label: '최대 파일 크기 (MB)',            type: 'number',
                                  restart: false, min: 1, max: 2000, step: 10,
                                  desc: '업로드 허용 최대 단일 파일 크기 (MB 단위)' },
                                { group: 'frontend', key: 'upload_auto_search_index', label: '업로드 후 검색 인덱스 자동 갱신', type: 'toggle',
                                  restart: false, desc: '업로드 완료 후 키워드(BM25) 검색 인덱스 자동 재생성' },
                                { group: 'frontend', key: 'upload_auto_vector_index', label: '업로드 후 벡터 인덱스 자동 갱신', type: 'toggle',
                                  restart: false, desc: '업로드 완료 후 FAISS 벡터 인덱스 자동 재생성 (시간 소요)' },
                            ]
                        },
                        {
                            title: '에디터',
                            fields: [
                                { group: 'frontend', key: 'editor_enabled',        label: '에디터 활성화',    type: 'toggle',
                                  restart: false, desc: '문서 인라인 편집 기능 활성화 여부' },
                                { group: 'frontend', key: 'editor_create_backup',  label: '저장 시 백업 생성', type: 'toggle',
                                  restart: false, desc: '파일 저장 전 .bak 백업 파일 생성' },
                                { group: 'frontend', key: 'editor_auto_save_interval', label: '자동 저장 간격 (ms)', type: 'number',
                                  restart: false, min: 5000, max: 300000, step: 5000,
                                  desc: '에디터 자동 저장 주기 (밀리초). 기본 30000 = 30초' },
                            ]
                        },
                    ]
                },
                {
                    tabId: 'tab-explorer-menu',
                    tabLabel: '메뉴 관리',
                    sections: []
                },
                {
                    tabId: 'tab-explorer-search',
                    tabLabel: '검색',
                    sections: [
                        {
                            title: '검색',
                            fields: [
                                { group: 'ai', key: 'default_search_type', label: '검색 방식', type: 'select',
                                  options: [['hybrid','하이브리드 (권장)'], ['keyword','키워드 (BM25)'], ['vector','벡터 유사도']],
                                  restart: false, desc: '문서 검색 알고리즘 선택' },
                                { group: 'ai', key: 'reranker_enabled', label: '리랭커 사용', type: 'toggle',
                                  restart: false, desc: 'Cross-encoder 리랭커로 검색 결과 정확도 향상' },
                                { group: 'ai', key: 'hybrid_keyword_weight', label: '키워드 비중 (하이브리드)', type: 'number',
                                  restart: false, min: 0, max: 1, step: 0.05,
                                  desc: '하이브리드 검색에서 BM25(키워드) 비중 (기본 0.3)' },
                                { group: 'ai', key: 'min_vector_score', label: '최소 벡터 유사도', type: 'number',
                                  restart: false, min: 0, max: 1, step: 0.01,
                                  desc: '이 값 미만의 벡터 유사도 결과는 제외 (기본 0.48)' },
                            ]
                        },
                    ]
                },
                {
                    tabId: 'tab-explorer-chatbot',
                    tabLabel: '챗봇',
                    sections: [
                        {
                            title: '챗봇',
                            fields: [
                                { group: 'frontend', key: 'ai_enabled', label: 'AI 챗봇 표시', type: 'toggle',
                                  restart: false, desc: 'Explorer 우측 하단 AI 챗봇 버튼 및 패널 표시 여부' },
                                { group: 'ai', key: 'chat_system_prompt', label: '시스템 프롬프트',
                                  type: 'textarea', restart: false, rows: 12,
                                  placeholder: '당신은 KF-21 전투기 기술 문서 전문 어시스턴트입니다. 제공된 참고 문서만을 기반으로 답변합니다.\n\n[핵심 규칙]\n1. 오직 제공된 문서 내용만 사용하여 답변합니다\n2. 문서에 없는 내용은 절대 추측하거나 일반 지식으로 보충하지 않습니다\n3. 정보가 없으면 "제공된 문서에서 해당 정보를 찾지 못했습니다"라고만 답변하고 끝냅니다\n4. "하지만", "일반적으로", "참고로" 등으로 문서 외 지식을 덧붙이지 않습니다\n\n[답변 형식]\n- 마크다운으로 답변합니다: **굵게**와 목록(- 또는 1.)만 사용합니다\n- 핵심 내용을 먼저 간결하게 제시하고, 필요한 경우만 목록으로 구조화합니다\n\n[언어]\n반드시 한국어로 답변합니다. 참고 문서가 영어여도 한국어로 번역하여 답변합니다.',
                                  desc: '챗봇이 답변 생성 시 따르는 지침. 비워두면 회색 글씨의 기본 프롬프트가 적용됩니다.' },
                                { group: 'ai', key: 'max_search_results', label: '참조 문서 수', type: 'number',
                                  restart: false, min: 1, max: 20, step: 1,
                                  desc: '챗봇 답변 생성 시 참조할 최대 문서 청크 수' },
                                { group: 'ai', key: 'query_rewrite_enabled', label: '쿼리 재작성', type: 'toggle',
                                  restart: false, desc: '멀티턴 대화에서 이전 문맥을 반영한 독립적 검색 쿼리 자동 재작성' },
                                { group: 'ai', key: 'max_context_length', label: '최대 컨텍스트 길이', type: 'number',
                                  restart: false, min: 1000, max: 32000, step: 500,
                                  desc: 'LLM에 전달하는 참고문서 최대 글자 수 (토큰 예산)' },
                                { group: 'session', key: 'max_conversation_turns', label: '최대 대화 턴 수', type: 'number',
                                  restart: false, min: 1, max: 20, step: 1,
                                  desc: '챗봇이 기억할 최대 대화 교환 횟수' },
                                { group: 'session', key: 'max_idle_minutes', label: '유휴 세션 만료 (분)', type: 'number',
                                  restart: false, min: 1, max: 1440, step: 5,
                                  desc: '마지막 메시지 이후 이 시간이 지나면 대화 세션 삭제' },
                            ]
                        },
                    ]
                },
            ]
        },
        // ── Notebook ──
        {
            id: 'notebook',
            label: 'Notebook',
            group: '설정',
            tabs: [
                {
                    tabId: 'tab-notebook-translation',
                    tabLabel: '번역',
                    sections: [
                        {
                            title: '모델',
                            fields: [
                                { group: 'translator', key: 'translation_model',
                                  label: 'Notebook 전용 모델 (오버라이드)', type: 'text', restart: false,
                                  placeholder: '플랫폼 AI 모델 사용',
                                  desc: '번역·요약에 사용할 모델. 비워두면 공통의 플랫폼 AI 모델을 사용합니다.' },
                            ]
                        },
                        {
                            title: 'PDF 번역',
                            fields: [
                                { group: 'translator', key: 'translate_table_text',
                                  label: '테이블 텍스트 번역', type: 'toggle', restart: false,
                                  desc: '표 안의 텍스트도 번역 대상에 포함' },
                                { group: 'translator', key: 'ocr_workaround',
                                  label: 'OCR 우회', type: 'toggle', restart: false,
                                  desc: '스캔 PDF에서 OCR 처리 활성화' },
                                { group: 'translator', key: 'custom_prompt',
                                  label: 'PDF 시스템 프롬프트', type: 'textarea', restart: false, rows: 4,
                                  desc: 'BabelDOC 시스템 프롬프트. 비워두면 기본 프롬프트 사용',
                                  placeholder: 'You are a professional $lang_out native translator...' },
                                { group: 'translator', key: 'disable_rich_text',
                                  label: '리치텍스트 번역 비활성화', type: 'toggle', restart: false,
                                  desc: '볼드/이탤릭 서식이 번역에서 제외됨' },
                                { group: 'translator', key: 'enhance_compatibility',
                                  label: '호환성 강화', type: 'toggle', restart: false,
                                  desc: '일부 PDF 뷰어 호환성 문제 해결' },
                            ]
                        },
                        {
                            title: '웹뷰 번역',
                            fields: [
                                { group: 'translator', key: 'web_table_mode',
                                  label: '표 추출 모드', type: 'select', restart: false,
                                  options: [['extract','구조 추출 (Markdown 테이블)'], ['image','이미지만'], ['off','끄기']],
                                  desc: '표 영역 처리 방식' },
                                { group: 'translator', key: 'web_formula_mode',
                                  label: '수식 추출 모드', type: 'select', restart: false,
                                  options: [['latex','LaTeX 변환'], ['image','이미지만'], ['off','끄기']],
                                  desc: '수식 영역 처리 방식' },
                                { group: 'translator', key: 'web_image_dpi',
                                  label: '이미지 해상도 (DPI)', type: 'range', restart: false,
                                  min: 72, max: 300, step: 6,
                                  desc: '추출 이미지의 해상도 (기본 150)' },
                            ]
                        },
                        {
                            title: 'AI 기능',
                            fields: [
                                { group: 'translator', key: 'web_auto_summary',
                                  label: '번역 완료 시 자동 요약', type: 'toggle', restart: false,
                                  desc: '웹 뷰 번역 완료 후 자동으로 문서 요약 생성' },
                                { group: 'translator', key: 'ai_translate_prompt',
                                  label: '선택 번역 프롬프트', type: 'textarea', restart: false, rows: 4,
                                  desc: '텍스트 선택 번역 시 Ollama에 전달되는 프롬프트' },
                                { group: 'translator', key: 'ai_summarize_prompt',
                                  label: '선택 요약 프롬프트', type: 'textarea', restart: false, rows: 4,
                                  desc: '텍스트 선택 요약 시 Ollama에 전달되는 프롬프트' },
                            ]
                        },
                        {
                            title: '성능',
                            fields: [
                                { group: 'translator', key: 'max_concurrent',
                                  label: '동시 번역 수', type: 'number', restart: false,
                                  min: 1, max: 16, step: 1,
                                  desc: 'GPU 부하 제한. 동시에 진행할 수 있는 최대 번역 작업 수' },
                                { group: 'translator', key: 'page_timeout',
                                  label: '페이지 타임아웃 (초)', type: 'number', restart: false,
                                  min: 60, max: 1800, step: 30,
                                  desc: '페이지당 최대 번역 시간 (기본 300초)' },
                            ]
                        },
                    ]
                }
            ]
        },
        // ── Verify ──
        {
            id: 'verify',
            label: 'Verify',
            group: '설정',
            tabs: [
                {
                    tabId: 'tab-verify-similarity',
                    tabLabel: '유사도 검사',
                    sections: [
                        {
                            title: '분류 임계값',
                            desc: '유사도 검사 엔진의 분류 기준. 값을 높이면 판정이 엄격해집니다.',
                            fields: [
                                { group: 'verify', key: 'sim_threshold_high', label: '동일 판정 기준 (L1)', type: 'range',
                                  restart: false, min: 0.5, max: 1.0, step: 0.05,
                                  desc: 'Winnowing 지문 일치율이 이 값 이상이면 "동일" 판정. 기본 0.85' },
                                { group: 'verify', key: 'sim_threshold_medium', label: '유사 판정 하한 (L3)', type: 'range',
                                  restart: false, min: 0.3, max: 0.9, step: 0.05,
                                  desc: '의미 유사도가 이 값 이상이면 매칭 후보로 포함. 기본 0.75' },
                            ]
                        },
                        {
                            title: '판정 라벨 경계',
                            desc: '전체 유사율(%)에 따라 표시되는 판정 라벨의 경계값.',
                            fields: [
                                { group: 'verify', key: 'sim_verdict_low', label: '양호/보통 경계 (%)', type: 'number',
                                  restart: false, min: 0, max: 100, step: 5, placeholder: '30',
                                  desc: '유사율이 이 값 미만이면 "양호". 기본 30%' },
                                { group: 'verify', key: 'sim_verdict_high', label: '보통/주의 경계 (%)', type: 'number',
                                  restart: false, min: 0, max: 100, step: 5, placeholder: '60',
                                  desc: '유사율이 이 값 이상이면 "주의". 기본 60%' },
                            ]
                        }
                    ]
                },
                {
                    tabId: 'tab-verify-compare',
                    tabLabel: 'AI 비교',
                    sections: [
                        {
                            title: 'AI 의미 분류',
                            fields: [
                                { group: 'compare', key: 'ai_enabled', label: 'AI 분석 활성화', type: 'toggle',
                                  restart: false, desc: '비교 모드에서 "AI 분석" 버튼 표시 여부' },
                                { group: 'compare', key: 'ai_system_prompt', label: '시스템 프롬프트',
                                  type: 'textarea', restart: false, rows: 16,
                                  placeholder: '당신은 기술문서 변경사항을 분류하는 전문가입니다.\n두 문서 버전 간의 변경 구간을 받아, 각 변경의 의미적 유형을 분류합니다.\n\n## 분류 태그 (정확히 6종 중 하나를 선택)\n\n- EDITORIAL: 편집상 변경...\n- CLARIFICATION: 기존 내용의 표현을 명확하게 보완...\n- STRICTER: 요구사항/기준/제약이 더 엄격해짐...\n- MORE_LENIENT: 요구사항/기준/제약이 완화됨...\n- EXPANDED: 기존에 없던 새 내용/범위/기능 추가...\n- RESTRUCTURED: 내용은 동일하나 위치/구조/번호 변경...',
                                  desc: '변경 구간 분류 시 LLM에 전달되는 지침. 비워두면 기본 프롬프트 적용' },
                                { group: 'compare', key: 'ai_model', label: 'Verify 전용 모델 (오버라이드)', type: 'text',
                                  restart: false, placeholder: '플랫폼 AI 모델 사용',
                                  desc: '비워두면 공통의 플랫폼 AI 모델을 사용합니다.' },
                                { group: 'compare', key: 'ai_temperature', label: '온도', type: 'range',
                                  restart: false, min: 0, max: 2, step: 0.1,
                                  desc: '0이면 결정적 출력. 높일수록 결과 다양성 증가' },
                            ]
                        },
                    ]
                },
                {
                    tabId: 'tab-verify-rules',
                    tabLabel: '규칙 관리',
                    sections: []
                }
            ]
        }
    ]
};

// ── 메인 렌더러 ───────────────────────────────────────────────────────────────

async function renderAdminSettings(container, opts) {
    // Plan-69: 컨테이너 파라미터화 — 기본값은 admin.html 의 #main-content (호출부 무변경)
    container = container || document.getElementById('main-content');
    opts = opts || {};
    if (!container) return;

    var _pageCls = (opts.mode === 'drawer') ? 'admin-settings-page admin-drawer-page' : 'admin-settings-page';
    container.innerHTML = '<div class="' + _pageCls + '"><div class="admin-settings-loading"><div class="network-spinner"><svg viewBox="0 0 32 50" fill="none"><line x1="8" y1="30" x2="18" y2="15" stroke="currentColor" stroke-width="2" stroke-linecap="round" opacity="0.3"/><line x1="18" y1="15" x2="24" y2="35" stroke="currentColor" stroke-width="2" stroke-linecap="round" opacity="0.3"/><line x1="24" y1="35" x2="8" y2="30" stroke="currentColor" stroke-width="2" stroke-linecap="round" opacity="0.3"/><circle class="ns-node-1" cx="8" cy="30" r="3.5" fill="currentColor"/><circle class="ns-node-2" cx="18" cy="15" r="3.5" fill="currentColor"/><circle class="ns-node-3" cx="24" cy="35" r="3.5" fill="currentColor"/><circle class="ns-particle" r="2" fill="currentColor" opacity="0.8"/></svg></div>설정 로드 중...</div></div>';
    // 드로어 모드에서는 호스트 페이지(Explorer 등)의 섹션 네비를 건드리지 않는다
    if (opts.mode !== 'drawer' && typeof updateSectionNav === 'function') updateSectionNav();

    var backendUrl = (typeof AUTH_CONFIG !== 'undefined' && 'backendUrl' in AUTH_CONFIG) ? AUTH_CONFIG.backendUrl : '';

    try {
        var r = await fetch(backendUrl + '/api/settings', { credentials: 'include' });
        if (r.status === 401) {
            if (typeof window.handleApiUnauthorized === 'function') window.handleApiUnauthorized();
            return;
        }
        if (r.status === 403) {
            container.innerHTML = '<div class="' + _pageCls + '"><div class="admin-settings-error"><span>🔒</span><p>관리자 권한이 필요합니다.</p></div></div>';
            return;
        }
        if (!r.ok) throw new Error('HTTP ' + r.status);

        var data = await r.json();
        _renderAdminSettingsUI(container, data.settings, opts);

    } catch (e) {
        container.innerHTML = '<div class="' + _pageCls + '"><div class="admin-settings-error"><span>⚠</span><p>설정을 불러올 수 없습니다.<br><small>' + _escHtml(e.message) + '</small></p></div></div>';
    }
}

// ── 현재 활성 시스템/탭 상태 ─────────────────────────────────────────────────
var _activeSystemId = null;
var _activeTabId = null;
var _currentSettings = null;
var _drawerMode = false;  // Plan-69: 드로어 렌더 여부 (사이드바·페이지헤더·무거운 확장 억제)

// ── UI 렌더링 ──────────────────────────────────────────────────────────────────

function _renderAdminSettingsUI(container, settings, opts) {
    opts = opts || {};
    _currentSettings = settings;
    _drawerMode = (opts.mode === 'drawer');

    // ── 드로어 모드 (Plan-69): 지정 시스템 탭만, 사이드바·페이지헤더 없이 ──
    if (_drawerMode) {
        // fetch 인플라이트 중 드로어가 닫혔으면(ESC 등) 뒤늦은 렌더 중단 — 잔여 렌더·상태 오염 방지
        if (!_drawerOpen) {
            _drawerMode = false;
            return;
        }
        var only = opts.only || [];
        var dsys = SETTINGS_SCHEMA.systems.filter(function(s) {
            return only.indexOf(s.id) !== -1 && !s.custom && s.tabs;
        });
        if (!dsys.length) {
            container.innerHTML = '<div class="admin-settings-page admin-drawer-page"><div class="admin-settings-error"><span>ℹ</span><p>이 시스템에는 조정 가능한 설정이 없습니다.</p></div></div>';
            return;
        }
        _activeSystemId = dsys[0].id;
        var dhtml = '<div class="admin-settings-page admin-drawer-page">';
        dhtml += '<div class="admin-settings-notice" id="admin-notice" style="display:none"></div>';
        dhtml += '<div class="admin-content" id="admin-content-area"></div>';
        dhtml += '</div>';
        container.innerHTML = dhtml;
        _renderSystemContent(dsys[0]);
        // 재시작 대기 상태 배너 복원 (드로어 안에서도 유지)
        if (_pendingRestartItems.length > 0) {
            _showNotice(
                'warn',
                '⚠ 다음 항목이 변경되어 <strong>서버 재시작이 필요</strong>합니다: ' +
                '<code>' + _pendingRestartItems.join(', ') + '</code>'
            );
        }
        return;
    }

    _activeSystemId = SETTINGS_SCHEMA.systems[0].id;

    var html = '<div class="admin-settings-page">';

    // 헤더
    html += '<div class="page-header">';
    html += '<div class="page-header-info">';
    html += '<h1 class="ph-icon-settings">관리자 설정</h1>';
    html += '</div>';
    html += '<div class="page-header-actions">';
    html += '<button class="btn btn-secondary admin-btn admin-btn-reset" onclick="_adminReset()">초기화</button>';
    html += '<button class="btn btn-primary admin-btn admin-btn-save" id="admin-save-btn" onclick="_adminSave()">저장</button>';
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
                } else if (field.type === 'number' || field.type === 'range') {
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

    // 이전 섹션이 대시보드였다면 자동 갱신 타이머를 여기서 해제한다.
    // 이 함수가 모든 섹션 렌더의 단일 통로라 해제 누락 지점이 생기지 않는다.
    if (typeof window.stopAnalyticsDashboard === 'function') window.stopAnalyticsDashboard();

    // 커스텀 패널
    if (sys.custom) {
        if (sys.id === 'users') { _renderUsersPanel(area); return; }
        if (sys.id === 'dashboard') { _renderDashboardPanel(area); return; }
        area.innerHTML = '';
        return;
    }

    // Plan-69: 드로어에서는 JS 주입/플레이스홀더 전용 탭(빈 sections — 메뉴 관리·규칙 관리)을 숨긴다
    var tabs = sys.tabs;
    if (_drawerMode) {
        tabs = tabs.filter(function(t) { return t.sections && t.sections.length > 0; });
    }

    var firstTab = tabs[0];
    _activeTabId = firstTab ? firstTab.tabId : null;
    var html = '';

    // 탭 바: 2개 이상일 때만 표시
    if (tabs.length >= 2) {
        html += '<div class="admin-tabs">';
        tabs.forEach(function(tab, idx) {
            html += '<button class="admin-tab-btn' + (idx === 0 ? ' active' : '') +
                    '" data-tab="' + tab.tabId + '" onclick="_adminSwitchTab(\'' + tab.tabId + '\')">' +
                    _escHtml(tab.tabLabel) + '</button>';
        });
        html += '</div>';
    }

    // 탭 패널
    tabs.forEach(function(tab, idx) {
        html += '<div class="admin-tab-panel' + (idx === 0 ? ' active' : '') + '" id="' + tab.tabId + '">';
        if (tab.sections.length === 0) {
            html += '<div class="admin-section"><p class="admin-section-desc" style="text-align:center;padding:40px 0;color:var(--text-muted)">향후 추가 예정입니다.</p></div>';
        }
        tab.sections.forEach(function(section) {
            var isCollapsed = section.collapsed;
            html += '<div class="admin-section' + (isCollapsed ? ' admin-section-collapsed' : '') + '">';
            html += '<h3 class="admin-section-title' + (isCollapsed ? ' admin-section-toggle' : '') + '"' +
                    (isCollapsed ? ' onclick="_adminToggleSection(this)" role="button" tabindex="0"' : '') + '>' +
                    _escHtml(section.title) +
                    (isCollapsed ? '<span class="admin-toggle-arrow">&#9654;</span>' : '') +
                    '</h3>';
            if (section.desc) html += '<p class="admin-section-desc">' + _escHtml(section.desc) + '</p>';

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

    // 메뉴 관리 탭 커스텀 렌더링 — 드로어에서는 제외 (무거운 관리는 admin.html 전용)
    if (sys.id === 'explorer' && !_drawerMode) { _renderMenuTab(); _renderExplorerDangerZone(); }
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
            return '<select class="form-select admin-select" id="' + id + '">' + opts + '</select>';
        }

        case 'range': {
            var rangeVal = (val !== undefined && val !== null) ? val : (field.min || 0);
            var minR = field.min !== undefined ? field.min : 0;
            var maxR = field.max !== undefined ? field.max : 100;
            var stepR = field.step !== undefined ? field.step : 1;
            var pct = ((rangeVal - minR) / (maxR - minR)) * 100;
            return '<div class="form-range-wrap">' +
                '<input type="range" class="form-range" id="' + id + '"' +
                ' value="' + rangeVal + '" min="' + minR + '" max="' + maxR + '" step="' + stepR + '"' +
                ' style="background:linear-gradient(to right,var(--active-color) ' + pct + '%,var(--border-color) ' + pct + '%)"' +
                ' oninput="this.style.background=\'linear-gradient(to right,var(--active-color) \'+((this.value-' + minR + ')/' + (maxR - minR) + ')*100+\'%,var(--border-color) \'+((this.value-' + minR + ')/' + (maxR - minR) + ')*100+\'%)\';this.nextElementSibling.textContent=this.value">' +
                '<span class="form-range-value">' + rangeVal + '</span>' +
                '</div>';
        }

        case 'number': {
            var attrs = ' value="' + (val !== undefined && val !== null ? val : '') + '"';
            if (field.min !== undefined) attrs += ' min="' + field.min + '"';
            if (field.max !== undefined) attrs += ' max="' + field.max + '"';
            if (field.step !== undefined) attrs += ' step="' + field.step + '"';
            var ph = field.placeholder ? ' placeholder="' + _escHtml(field.placeholder) + '"' : '';
            return '<input type="number" class="form-input admin-input admin-number" id="' + id + '"' + attrs + ph + '>';
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

        default: { // text
            var ph = field.placeholder ? ' placeholder="' + _escHtml(field.placeholder) + '"' : '';
            return '<input type="text" class="form-input admin-input" id="' + id + '" value="' +
                _escHtml(val !== undefined && val !== null ? String(val) : '') + '"' + ph + '>';
        }
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

// ── 고급 섹션 토글 ──────────────────────────────────────────────────────────

function _adminToggleSection(titleEl) {
    var section = titleEl.closest('.admin-section');
    if (!section) return;
    section.classList.toggle('admin-section-collapsed');
    var arrow = titleEl.querySelector('.admin-toggle-arrow');
    if (arrow) arrow.textContent = section.classList.contains('admin-section-collapsed') ? '\u25B6' : '\u25BC';
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
                        var v = groupData[field.key];
                        if (v !== null && v !== undefined && v !== '') {
                            result[field.group][field.key] = v;
                        }
                    }
                });
            });
        });
    });
    return result;
}

// ── 저장 ─────────────────────────────────────────────────────────────────────

async function _adminSave() {
    // 설정 로드 실패 상태(예: 드로어 열 때 백엔드 다운)에서 저장 클릭 시 null deref 방지
    if (!_currentSettings) { showToast('설정을 불러오지 못해 저장할 수 없습니다', 'error'); return; }
    var saveBtn = document.getElementById('admin-save-btn');
    if (saveBtn) { saveBtn.disabled = true; saveBtn.textContent = '저장 중...'; }

    _hideNotice();

    var settings = _collectSettings();
    var backendUrl = (typeof AUTH_CONFIG !== 'undefined' && 'backendUrl' in AUTH_CONFIG) ? AUTH_CONFIG.backendUrl : '';

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
            // 즉시 피드백(스크롤 중에도 보이도록) — 재시작 대기 목록은 상단 배너로 지속 표시(리마인더)
            showToast('저장됨 — 일부 항목은 서버 재시작 후 적용됩니다', 'warning', 6000);
            _showNotice(
                'warn',
                '⚠ 다음 항목은 <strong>서버 재시작 후</strong> 적용됩니다: ' +
                '<code>' + _pendingRestartItems.join(', ') + '</code>'
            );
        } else {
            showToast('설정이 저장되어 즉시 적용되었습니다', 'success');
        }

    } catch (e) {
        showToast('저장 실패: ' + e.message, 'error');
    } finally {
        if (saveBtn) { saveBtn.disabled = false; saveBtn.textContent = '저장'; }
    }
}

// ── 초기화 ────────────────────────────────────────────────────────────────────

async function _adminReset() {
    if (!confirm('모든 설정을 기본값으로 초기화하시겠습니까?\n저장된 settings.json이 삭제됩니다.')) return;

    var backendUrl = (typeof AUTH_CONFIG !== 'undefined' && 'backendUrl' in AUTH_CONFIG) ? AUTH_CONFIG.backendUrl : '';

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
// ── 빠른 설정 드로어 (Plan-69) — 각 서브시스템에서 페이지 전환 없이 그 시스템 설정 조정
// ══════════════════════════════════════════════════════════════════════════════

var _settingsDrawerEl = null;
var _drawerLastFocus = null;
var _drawerOpen = false;  // 동기 열림 상태 (렌더 인플라이트 중 닫힘 감지용 — .open 은 rAF 비동기라 부적합)

function _buildSettingsDrawer() {
    if (_settingsDrawerEl) return _settingsDrawerEl;

    var overlay = document.createElement('div');
    overlay.className = 'modal-overlay settings-drawer-overlay';
    overlay.innerHTML =
        '<aside class="settings-drawer" role="dialog" aria-modal="true" aria-label="빠른 설정">' +
            '<div class="settings-drawer-header">' +
                '<h3 class="settings-drawer-title">빠른 설정</h3>' +
                '<button type="button" class="modal-close settings-drawer-close" aria-label="닫기">&times;</button>' +
            '</div>' +
            '<div class="settings-drawer-body admin-drawer-scope"></div>' +
            '<div class="settings-drawer-footer">' +
                '<a class="settings-drawer-fulllink" href="admin.html">전체 관리자 설정 열기 →</a>' +
                '<button type="button" class="btn btn-primary" id="admin-save-btn" onclick="_adminSave()">저장</button>' +
            '</div>' +
        '</aside>';

    // 배경 클릭 닫기 (드로어 내부 클릭은 유지)
    overlay.addEventListener('click', function(e) {
        if (e.target === overlay) closeSettingsDrawer();
    });
    overlay.querySelector('.settings-drawer-close').addEventListener('click', closeSettingsDrawer);

    document.body.appendChild(overlay);
    _settingsDrawerEl = overlay;
    return overlay;
}

function openSettingsDrawer(systemId) {
    if (!systemId) return;
    var sys = null;
    SETTINGS_SCHEMA.systems.forEach(function(s) { if (s.id === systemId) sys = s; });
    if (!sys) { showToast('이 시스템의 설정이 없습니다', 'info'); return; }

    _drawerLastFocus = document.activeElement;
    _drawerOpen = true;
    _buildSettingsDrawer();

    _settingsDrawerEl.querySelector('.settings-drawer-title').textContent =
        (sys.label || '설정') + ' 빠른 설정';
    var body = _settingsDrawerEl.querySelector('.settings-drawer-body');

    // 열림 (다음 프레임에 트랜지션 트리거) + 포커스를 드로어 안으로 이동(트랩 진입점)
    _settingsDrawerEl.classList.remove('closing');
    requestAnimationFrame(function() {
        _settingsDrawerEl.classList.add('open');
        var closeBtn = _settingsDrawerEl.querySelector('.settings-drawer-close');
        if (closeBtn) closeBtn.focus();
    });
    document.addEventListener('keydown', _drawerKeydown);

    renderAdminSettings(body, { only: [systemId], mode: 'drawer' });
}

function closeSettingsDrawer() {
    if (!_settingsDrawerEl) return;
    _drawerOpen = false;
    _settingsDrawerEl.classList.remove('open');
    document.removeEventListener('keydown', _drawerKeydown);

    // teardown — 드로어 전용 렌더 상태 정리 (D1: 잔여 방지)
    _drawerMode = false;
    _currentSettings = null;  // 재오픈 실패 시 이전 스냅샷 저장(stale POST) 방지 — 저장은 null 가드로 차단
    var body = _settingsDrawerEl.querySelector('.settings-drawer-body');
    if (body) body.innerHTML = '';

    if (_drawerLastFocus && typeof _drawerLastFocus.focus === 'function') {
        _drawerLastFocus.focus();
    }
    _drawerLastFocus = null;
}

// ESC 닫기 + 포커스 트랩 (D1)
function _drawerKeydown(e) {
    if (e.key === 'Escape') { e.preventDefault(); closeSettingsDrawer(); return; }
    if (e.key !== 'Tab' || !_settingsDrawerEl) return;

    var focusables = _settingsDrawerEl.querySelectorAll(
        'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
    );
    if (!focusables.length) return;
    var first = focusables[0];
    var last = focusables[focusables.length - 1];
    if (e.shiftKey && document.activeElement === first) {
        e.preventDefault(); last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault(); first.focus();
    }
}

// ══════════════════════════════════════════════════════════════════════════════
// ── 메뉴 관리 탭 ─────────────────────────────────────────────────────────────
// ══════════════════════════════════════════════════════════════════════════════

var _menuEditorData = null;
var _menuEditorOriginal = null;  // 마지막 로드/저장 시점 스냅샷 (dirty 판정용, Plan-67)
// '추가' 로 만들었지만 아직 확인하지 않은 노드 — 취소 시 되돌린다.
// 인덱스는 이동·삭제로 흔들리므로 노드 참조로 보관한다.
var _menuPendingNew = null;

function _renderMenuTab() {
    var panel = document.getElementById('tab-explorer-menu');
    if (!panel) return;

    panel.innerHTML =
        '<div class="admin-section">' +
            '<h3 class="admin-section-title">\uBA54\uB274 \uAD6C\uC870 \uD3B8\uC9D1</h3>' +
            '<div class="menu-editor">' +
                '<div class="menu-editor-loading"><div class="network-spinner"><svg viewBox="0 0 32 50" fill="none"><line x1="8" y1="30" x2="18" y2="15" stroke="currentColor" stroke-width="2" stroke-linecap="round" opacity="0.3"/><line x1="18" y1="15" x2="24" y2="35" stroke="currentColor" stroke-width="2" stroke-linecap="round" opacity="0.3"/><line x1="24" y1="35" x2="8" y2="30" stroke="currentColor" stroke-width="2" stroke-linecap="round" opacity="0.3"/><circle class="ns-node-1" cx="8" cy="30" r="3.5" fill="currentColor"/><circle class="ns-node-2" cx="18" cy="15" r="3.5" fill="currentColor"/><circle class="ns-node-3" cx="24" cy="35" r="3.5" fill="currentColor"/><circle class="ns-particle" r="2" fill="currentColor" opacity="0.8"/></svg></div> \uBA54\uB274 \uB85C\uB4DC \uC911...</div>' +
            '</div>' +
        '</div>';

    _menuFetchData();
}

// ── Explorer 콘텐츠 올클린 초기화 (Plan-68 Phase 4) ────────────────────────────
// 콘텐츠 탭 하단에 위험 섹션 주입. 업로드/작성 문서만 휴지통 이동(시스템·계정·통계 보존).

function _renderExplorerDangerZone() {
    var panel = document.getElementById('tab-explorer-content');
    if (!panel || document.getElementById('explorer-allclean-section')) return;

    var sec = document.createElement('div');
    sec.className = 'admin-section';
    sec.id = 'explorer-allclean-section';
    sec.innerHTML =
        '<h3 class="admin-section-title">콘텐츠 초기화 (위험)</h3>' +
        '<div class="admin-field-desc" style="margin-bottom:12px">' +
            '업로드·작성으로 추가된 <b>사용자 문서를 전부 휴지통으로 이동</b>하여 Explorer를 처음 설치 상태로 되돌립니다. ' +
            '시스템 페이지·가이드·화면 디자인, 계정·통계·설정은 <b>보존</b>됩니다. ' +
            '<span style="opacity:.7">삭제분은 <code>data/trash/</code> 에 보관되어 수동 복구 가능.</span>' +
        '</div>' +
        '<button class="btn btn-danger admin-btn" id="explorer-allclean-btn">Explorer 콘텐츠 초기화</button>';
    panel.appendChild(sec);

    var btn = document.getElementById('explorer-allclean-btn');
    if (btn) btn.addEventListener('click', _explorerAllCleanModal);
}

function _explorerAllCleanModal() {
    var overlay = document.createElement('div');
    overlay.id = 'explorer-allclean-overlay';
    overlay.className = 'admin-modal-overlay';
    overlay.innerHTML =
        '<div class="admin-modal">' +
            '<h3>Explorer 콘텐츠 초기화 — 되돌리기 어려움</h3>' +
            '<div id="allclean-body" style="margin:8px 0 16px;font-size:13px;line-height:1.75">' +
                '<b>사용자가 올리거나 작성한 문서 전부</b>가 휴지통으로 이동합니다.<br>' +
                '<span style="opacity:.75">보존: 시스템 페이지·가이드·화면 디자인 · 계정 · 통계 · 설정</span><br>' +
                '<span style="opacity:.75">삭제분은 <code>data/trash/</code> 에 보관(수동 복구 가능).</span>' +
                '<div style="margin-top:14px">계속하려면 아래에 <b>초기화</b> 를 입력하세요.</div>' +
                '<input type="text" id="allclean-confirm-input" class="form-input" autocomplete="off" ' +
                    'placeholder="초기화" style="margin-top:6px;width:100%">' +
            '</div>' +
            '<div style="display:flex;gap:8px;justify-content:flex-end">' +
                '<button class="btn btn-secondary admin-btn" id="allclean-cancel">취소</button>' +
                '<button class="btn btn-danger admin-btn" id="allclean-confirm" disabled>초기화 실행</button>' +
            '</div>' +
        '</div>';
    document.body.appendChild(overlay);

    var input = document.getElementById('allclean-confirm-input');
    var confirmBtn = document.getElementById('allclean-confirm');
    var cancelBtn = document.getElementById('allclean-cancel');

    // Escape 는 document 에 건다 — 포커스가 모달 밖에 있어도 닫히도록.
    // 단 초기화가 시작된 뒤에는 취소 버튼과 동일하게 닫기를 막는다.
    function onEscape(e) {
        if (e.key !== 'Escape') return;
        if (cancelBtn && cancelBtn.disabled) return;
        close();
    }
    function close() {
        document.removeEventListener('keydown', onEscape);
        overlay.remove();
    }
    document.addEventListener('keydown', onEscape);

    cancelBtn.addEventListener('click', close);
    overlay.addEventListener('click', function(e) { if (e.target === overlay) close(); });
    input.addEventListener('input', function() {
        confirmBtn.disabled = (input.value.trim() !== '초기화');
    });
    confirmBtn.addEventListener('click', function() { _runExplorerAllClean(overlay, close); });
    input.focus();
}

// close: 모달 teardown 단일 통로 (Escape 리스너 해제 포함) — overlay.remove() 직접 호출 금지
async function _runExplorerAllClean(overlay, close) {
    var backendUrl = (typeof AUTH_CONFIG !== 'undefined' && 'backendUrl' in AUTH_CONFIG) ? AUTH_CONFIG.backendUrl : '';
    var body = document.getElementById('allclean-body');
    var cancelBtn = document.getElementById('allclean-cancel');
    var confirmBtn = document.getElementById('allclean-confirm');
    if (confirmBtn) confirmBtn.disabled = true;
    if (cancelBtn) cancelBtn.disabled = true;
    if (body) body.innerHTML = '<div id="allclean-progress"><span class="spinner spinner-sm"></span> 초기화 진행 중…</div>';

    function step(msg) {
        var p = document.getElementById('allclean-progress');
        if (p) p.innerHTML = '<span class="spinner spinner-sm"></span> ' + _escHtml(msg);
    }

    try {
        var res = await fetch(backendUrl + '/api/explorer/all-clean', { method: 'POST', credentials: 'include' });
        if (res.status === 401) {
            if (typeof window.handleApiUnauthorized === 'function') window.handleApiUnauthorized();
            close();
            return;
        }
        if (!res.ok || !res.body) throw new Error('HTTP ' + res.status);

        var reader = res.body.getReader();
        var decoder = new TextDecoder();
        var buffer = '';
        var final = null;
        while (true) {
            var chunk = await reader.read();
            if (chunk.done) break;
            buffer += decoder.decode(chunk.value, { stream: true });
            var lines = buffer.split('\n');
            buffer = lines.pop();
            for (var i = 0; i < lines.length; i++) {
                var line = lines[i].trim();
                if (!line) continue;
                var ev;
                try { ev = JSON.parse(line); } catch (e) { continue; }
                if (ev.message) step(ev.message);
                if (ev.step === 'done') final = ev;
            }
        }

        close();
        if (final && final.success) {
            var n = (final.trashed != null) ? final.trashed + '개 항목 정리' : '완료';
            showToast('Explorer 초기화 완료 — ' + n + ' (휴지통 보관)', 'success');
        } else {
            showToast('초기화 실패: ' + (final && final.message ? final.message : '알 수 없는 오류'), 'error');
        }
        renderAdminSettings();
    } catch (e) {
        close();
        showToast('초기화 실패: ' + e.message, 'error');
    }
}

async function _menuFetchData() {
    var backendUrl = (typeof AUTH_CONFIG !== 'undefined' && 'backendUrl' in AUTH_CONFIG) ? AUTH_CONFIG.backendUrl : '';
    try {
        var r = await fetch(backendUrl + '/api/menu', { credentials: 'include' });
        if (r.status === 401) {
            if (typeof window.handleApiUnauthorized === 'function') window.handleApiUnauthorized();
            return;
        }
        if (!r.ok) throw new Error('HTTP ' + r.status);
        var data = await r.json();
        _menuEditorData = data.menu || [];
        _menuEditorOriginal = JSON.stringify(_menuEditorData);
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
    html += '<button class="btn btn-primary admin-btn admin-btn-save" onclick="_menuAddTopLevel()" style="padding:6px 14px;font-size:12px;">+ \uCD5C\uC0C1\uC704 \uD56D\uBAA9 \uCD94\uAC00</button>';
    html += '</div>';
    html += '<div class="menu-tree">';
    if (_menuEditorData && _menuEditorData.length > 0) {
        html += _menuRenderNodes(_menuEditorData, 0, []);
    } else {
        html += '<div class="menu-tree-empty">\uBA54\uB274 \uD56D\uBAA9\uC774 \uC5C6\uC2B5\uB2C8\uB2E4. \uC704 \uBC84\uD2BC\uC73C\uB85C \uCD94\uAC00\uD558\uC138\uC694.</div>';
    }
    html += '</div>';
    html += '<div class="menu-editor-actions">';
    html += '<button class="btn btn-primary admin-btn admin-btn-save" onclick="_menuSave()">\uC800\uC7A5</button>';
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
    if (node.url) {
        html += '<button class="menu-btn" title="\uBB38\uC11C\uB9CC \uC81C\uAC70 (\uB178\uB4DC \uC720\uC9C0)" onclick="_menuDetachByPath(\'' + pathStr + '\')">\u2298</button>';
    }
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
    var node = { label: '\uC0C8 \uD56D\uBAA9' };
    _menuEditorData.push(node);
    _menuRenderEditor();
    _menuEditByPath(String(_menuEditorData.length - 1), { list: _menuEditorData, node: node });
}

function _menuAddChildByPath(pathStr) {
    var path = _menuParsePath(pathStr);
    var ctx = _menuNodeByPath(path);
    if (!ctx || !ctx.node) return;
    // children \uBC30\uC5F4\uC744 \uC5EC\uAE30\uC11C \uCC98\uC74C \uB9CC\uB4E4\uC5C8\uB2E4\uBA74 \uCDE8\uC18C \uC2DC \uADF8\uAC83\uAE4C\uC9C0 \uB418\uB3CC\uB824\uC57C dirty \uAC00 \uB0A8\uC9C0 \uC54A\uB294\uB2E4
    var createdList = !ctx.node.children;
    if (createdList) ctx.node.children = [];
    var node = { label: '\uC0C8 \uD56D\uBAA9' };
    ctx.node.children.push(node);
    _menuRenderEditor();
    _menuEditByPath(path.concat([ctx.node.children.length - 1]).join(','),
                    { list: ctx.node.children, node: node, parent: ctx.node, createdList: createdList });
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

function _menuIsDirty() {
    return JSON.stringify(_menuEditorData) !== _menuEditorOriginal;
}

function _menuDeleteByPath(pathStr) {
    var path = _menuParsePath(pathStr);
    var ctx = _menuNodeByPath(path);
    if (!ctx || !ctx.node) return;

    var linkedUrls = _menuCollectUrls(ctx.node);
    var hasChildren = ctx.node.children && ctx.node.children.length > 0;

    // \uBB38\uC11C(\uB9C1\uD06C) \uC5C6\uB294 \uBE48 \uD56D\uBAA9/\uCE74\uD14C\uACE0\uB9AC \u2192 \uAE30\uC874 \uC2A4\uD14C\uC774\uC9D5 splice (\uC800\uC7A5 \uC2DC \uBC18\uC601)
    if (linkedUrls.length === 0) {
        var m = '"' + ctx.node.label + '"';
        m += hasChildren ? ' \uD56D\uBAA9\uACFC \uD558\uC704 ' + ctx.node.children.length + '\uAC1C\uB97C \uC0AD\uC81C\uD569\uB2C8\uB2E4.' : ' \uD56D\uBAA9\uC744 \uC0AD\uC81C\uD569\uB2C8\uB2E4.';
        m += '\n\n\uC0AD\uC81C\uD558\uC2DC\uACA0\uC2B5\uB2C8\uAE4C? (\uC800\uC7A5 \uC2DC \uBC18\uC601)';
        if (!confirm(m)) return;
        ctx.parentList.splice(ctx.index, 1);
        _menuRenderEditor();
        return;
    }

    // \uBB38\uC11C \uBCF4\uC720 \u2192 \uC989\uC2DC cascade \uC0AD\uC81C (\uD30C\uC77C \uD734\uC9C0\uD1B5 + \uC778\uB371\uC2A4 \uC81C\uAC70 + \uB178\uB4DC \uC81C\uAC70)
    if (_menuIsDirty()) {
        showToast('\uC800\uC7A5\uB418\uC9C0 \uC54A\uC740 \uD3B8\uC9D1\uC774 \uC788\uC2B5\uB2C8\uB2E4. \uBA3C\uC800 [\uC800\uC7A5] \uD6C4 \uBB38\uC11C\uB97C \uC0AD\uC81C\uD558\uC138\uC694', 'warning', 4000);
        return;
    }
    _openDocDeleteModal(linkedUrls, { keepNodes: false, label: ctx.node.label });
}

function _menuDetachByPath(pathStr) {
    var path = _menuParsePath(pathStr);
    var ctx = _menuNodeByPath(path);
    if (!ctx || !ctx.node || !ctx.node.url) return;
    if (_menuIsDirty()) {
        showToast('\uC800\uC7A5\uB418\uC9C0 \uC54A\uC740 \uD3B8\uC9D1\uC774 \uC788\uC2B5\uB2C8\uB2E4. \uBA3C\uC800 [\uC800\uC7A5] \uD6C4 \uC9C4\uD589\uD558\uC138\uC694', 'warning', 4000);
        return;
    }
    _openDocDeleteModal([ctx.node.url], { keepNodes: true, label: ctx.node.label });
}

// \uBB38\uC11C \uC0AD\uC81C/\uBD84\uB9AC \u2014 \uC601\uD5A5 \uBBF8\uB9AC\uBCF4\uAE30 \uBAA8\uB2EC \u2192 \uD655\uC778 \u2192 \uC989\uC2DC cascade (Plan-67)
function _openDocDeleteModal(urls, opts) {
    var backendUrl = (typeof AUTH_CONFIG !== 'undefined' && 'backendUrl' in AUTH_CONFIG) ? AUTH_CONFIG.backendUrl : '';
    var existing = document.getElementById('doc-delete-overlay');
    if (existing) existing.remove();

    var isDetach = !!opts.keepNodes;
    var verb = isDetach ? '\uBB38\uC11C\uB9CC \uC81C\uAC70' : '\uC0AD\uC81C';

    var overlay = document.createElement('div');
    overlay.id = 'doc-delete-overlay';
    overlay.className = 'admin-modal-overlay';
    overlay.innerHTML =
        '<div class="admin-modal">' +
            '<h3>' + _escHtml(opts.label || '') + ' \u2014 ' + verb + '</h3>' +
            '<div id="doc-delete-impact" style="margin:8px 0 16px;font-size:13px;line-height:1.75">' +
                '<span class="spinner spinner-sm"></span> \uC601\uD5A5 \uBD84\uC11D \uC911\u2026' +
            '</div>' +
            '<div style="display:flex;gap:8px;justify-content:flex-end">' +
                '<button class="btn btn-secondary admin-btn" id="doc-delete-cancel">\uCDE8\uC18C</button>' +
                '<button class="btn btn-danger admin-btn" id="doc-delete-confirm" disabled>' + verb + '</button>' +
            '</div>' +
        '</div>';
    document.body.appendChild(overlay);

    // Escape 는 document 에 건다 — 포커스가 모달 밖에 있어도 닫히도록
    function onEscape(e) { if (e.key === 'Escape') close(); }
    function close() {
        document.removeEventListener('keydown', onEscape);
        overlay.remove();
    }
    document.addEventListener('keydown', onEscape);

    document.getElementById('doc-delete-cancel').addEventListener('click', close);
    overlay.addEventListener('click', function(e) { if (e.target === overlay) close(); });

    fetch(backendUrl + '/api/document-impact', {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ urls: urls })
    }).then(function(r) {
        if (r.status === 401) { if (typeof window.handleApiUnauthorized === 'function') window.handleApiUnauthorized(); return null; }
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
    }).then(function(imp) {
        if (!imp) return;
        var el = document.getElementById('doc-delete-impact');
        if (!el) return;
        // \uC11C\uBC84 \uC720\uB798 \uC22B\uC790\uAC12\uC740 Number() \uAC15\uC81C \uBCC0\uD658 \uD6C4 \uC0BD\uC785 (\uBC29\uC5B4\uC801, code-review W2)
        var nFiles = Number(imp.files) || 0;
        var nSearch = Number(imp.search_sections) || 0;
        var nVector = Number(imp.vector_sections) || 0;
        var nRef = Number(imp.ref_nodes) || 0;
        var rows =
            '\u2022 \uBB38\uC11C \uD30C\uC77C: <b>' + nFiles + '</b>\uAC1C \u2192 <code>data/trash/</code> \uB85C \uC774\uB3D9<br>' +
            '\u2022 \uAC80\uC0C9 \uC778\uB371\uC2A4: <b>' + nSearch + '</b> \uC139\uC158 \uC81C\uAC70<br>' +
            '\u2022 AI(\uBCA1\uD130) \uC778\uB371\uC2A4: <b>' + nVector + '</b> \uC139\uC158 \uC81C\uAC70';
        if (nRef > 1) {
            rows += '<br>\u2022 \u26A0 \uC774 \uBB38\uC11C\uB97C \uCC38\uC870\uD558\uB294 \uBA54\uB274 \uB178\uB4DC <b>' + nRef + '</b>\uAC1C \u2014 \uBAA8\uB450 ' + (isDetach ? '\uBD84\uB9AC' : '\uC815\uB9AC') + '\uB429\uB2C8\uB2E4';
        }
        rows += '<br><span style="opacity:.65">\uD30C\uC77C\uC740 \uC601\uAD6C \uC0AD\uC81C\uAC00 \uC544\uB2C8\uB77C \uD734\uC9C0\uD1B5 \uD3F4\uB354\uB85C \uC774\uB3D9\uD569\uB2C8\uB2E4 (\uC218\uB3D9 \uBCF5\uAD6C \uAC00\uB2A5).</span>';
        if (isDetach) rows += '<br><span style="opacity:.65">\uBA54\uB274 \uB178\uB4DC\uB294 \uC720\uC9C0\uB418\uACE0 \uBB38\uC11C \uB9C1\uD06C\uB9CC \uC81C\uAC70\uB429\uB2C8\uB2E4.</span>';
        el.innerHTML = rows;
        var okBtn = document.getElementById('doc-delete-confirm');
        if (okBtn) okBtn.disabled = false;
    }).catch(function(e) {
        var el = document.getElementById('doc-delete-impact');
        if (el) el.innerHTML = '<span style="color:var(--color-error)">\uC601\uD5A5 \uBD84\uC11D \uC2E4\uD328: ' + _escHtml(e.message) + '</span>';
    });

    document.getElementById('doc-delete-confirm').addEventListener('click', function() {
        var btn = this;
        btn.disabled = true; btn.textContent = '\uCC98\uB9AC \uC911\u2026';
        fetch(backendUrl + '/api/document-delete', {
            method: 'POST', credentials: 'include',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ urls: urls, keep_nodes: isDetach })
        }).then(function(r) {
            if (r.status === 401) { if (typeof window.handleApiUnauthorized === 'function') window.handleApiUnauthorized(); return null; }
            if (!r.ok) return r.json().then(function(err) { throw new Error(err.detail || ('HTTP ' + r.status)); });
            return r.json();
        }).then(function(res) {
            if (!res) return;
            close();
            _menuFetchData();                                       // \uD3B8\uC9D1\uAE30 \uC7AC\uB3D9\uAE30\uD654 (\uC11C\uBC84 menu.json \uAE30\uC900)
            if (typeof loadMenuData === 'function') loadMenuData();  // \uC88C\uCE21 \uD2B8\uB9AC \uAC31\uC2E0
            showToast(isDetach ? '\uBB38\uC11C\uB97C \uC81C\uAC70\uD588\uC2B5\uB2C8\uB2E4 (\uB178\uB4DC \uC720\uC9C0)' : '\uBB38\uC11C\uB97C \uC0AD\uC81C\uD588\uC2B5\uB2C8\uB2E4 (\uD734\uC9C0\uD1B5 \uC774\uB3D9)', 'success');
        }).catch(function(e) {
            close();
            showToast('\uC0AD\uC81C \uC2E4\uD328: ' + e.message, 'error');
        });
    });
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

function _menuEditByPath(pathStr, pendingNew) {
    // 다른 편집을 열면 이전 '추가 대기' 추적은 포기한다 (되돌릴 시점을 놓친 것)
    _menuPendingNew = pendingNew || null;

    var path = _menuParsePath(pathStr);
    var ctx = _menuNodeByPath(path);
    if (!ctx || !ctx.node) return;

    var nodeEl = document.querySelector('.menu-node[data-path="' + pathStr + '"]');
    if (!nodeEl) return;
    var rowEl = nodeEl.querySelector(':scope > .menu-node-row');
    if (!rowEl) return;

    var editHtml =
        '<div class="menu-node-edit" style="padding-left:' + rowEl.style.paddingLeft + '">' +
            '<input class="form-input admin-input menu-edit-label" placeholder="\uC774\uB984" value="' + _escHtml(ctx.node.label || '') + '">' +
            '<input class="form-input admin-input menu-edit-url" placeholder="URL (\uBE44\uC6CC\uB450\uBA74 \uD3F4\uB354)" value="' + _escHtml(ctx.node.url || '') + '">' +
            '<button class="btn btn-secondary btn-sm" onclick="_menuEditCancel()">\uCDE8\uC18C</button>' +
            '<button class="btn btn-primary btn-sm menu-edit-confirm" onclick="_menuEditConfirm(\'' + pathStr + '\',this)">\uD655\uC778</button>' +
        '</div>';

    rowEl.style.display = 'none';
    rowEl.insertAdjacentHTML('afterend', editHtml);

    var labelInput = nodeEl.querySelector('.menu-edit-label');
    if (labelInput) { labelInput.focus(); labelInput.select(); }

    var editDiv = nodeEl.querySelector('.menu-node-edit');
    if (editDiv) {
        editDiv.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') _menuEditConfirm(pathStr, editDiv.querySelector('.menu-edit-confirm'));
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
    _menuPendingNew = null;   // 확인됨 — 더 이상 되돌릴 대상 아님
    _menuRenderEditor();
}

function _menuEditCancel() {
    // 취소는 흔적을 남기지 않는다 — '추가' 로 방금 만든 노드는 되돌린다
    if (_menuPendingNew) {
        var i = _menuPendingNew.list.indexOf(_menuPendingNew.node);
        if (i >= 0) _menuPendingNew.list.splice(i, 1);
        if (_menuPendingNew.createdList && _menuPendingNew.list.length === 0) {
            delete _menuPendingNew.parent.children;
        }
        _menuPendingNew = null;
    }
    _menuRenderEditor();
}

// ── 메뉴 저장 ─────────────────────────────────────────────────────────────────

async function _menuSave() {
    var saveBtn = document.querySelector('.menu-editor-actions .admin-btn-save');
    if (saveBtn) { saveBtn.disabled = true; saveBtn.textContent = '\uC800\uC7A5 \uC911...'; }

    var backendUrl = (typeof AUTH_CONFIG !== 'undefined' && 'backendUrl' in AUTH_CONFIG) ? AUTH_CONFIG.backendUrl : '';

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

        showToast('\uBA54\uB274\uAC00 \uC800\uC7A5\uB418\uC5C8\uC2B5\uB2C8\uB2E4', 'success');

        _menuEditorOriginal = JSON.stringify(_menuEditorData);  // 저장 후 dirty 해제

        // 좌측 패널 갱신
        if (typeof loadMenuData === 'function') loadMenuData();

    } catch (e) {
        showToast('\uBA54\uB274 \uC800\uC7A5 \uC2E4\uD328: ' + e.message, 'error');
    } finally {
        if (saveBtn) { saveBtn.disabled = false; saveBtn.textContent = '\uC800\uC7A5'; }
    }
}

// ══════════════════════════════════════════════════════════════════════════════
//  계정 관리 패널
// ══════════════════════════════════════════════════════════════════════════════

function _renderUsersPanel(area) {
    var backendUrl = (typeof AUTH_CONFIG !== 'undefined' && 'backendUrl' in AUTH_CONFIG) ? AUTH_CONFIG.backendUrl : '';

    area.innerHTML =
        '<div class="admin-section">' +
            '<div class="admin-section-header">' +
                '<h3 class="admin-section-title">사용자 목록</h3>' +
                '<button class="btn btn-primary btn-sm" id="admin-add-user-btn">+ 사용자 추가</button>' +
            '</div>' +
            '<div class="admin-users-table-wrap">' +
                '<table class="admin-users-table">' +
                    '<thead><tr><th>ID</th><th>Username</th><th>Name</th><th>Role</th><th>IP</th><th>Last Login</th><th>Created</th><th>Actions</th></tr></thead>' +
                    '<tbody id="admin-users-tbody"></tbody>' +
                '</table>' +
            '</div>' +
        '</div>';

    _loadUsersTable(backendUrl);

    document.getElementById('admin-add-user-btn').addEventListener('click', function() {
        _addUserModal(backendUrl);
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
            var displayName = u.name || '-';
            var nameTooltip = u.description ? _escHtml(u.description) : (u.name ? '' : 'Name/Description 미입력');
            var lastLogin = _formatLastLogin(u.last_login_at);

            var editBtn = document.createElement('button');
            editBtn.className = 'admin-btn-sm';
            editBtn.textContent = 'Edit';
            editBtn.addEventListener('click', function() {
                _editUserInline(backendUrl, u);
            });
            var delBtn = document.createElement('button');
            delBtn.className = 'admin-btn-sm admin-btn-danger';
            delBtn.textContent = 'Delete';
            delBtn.addEventListener('click', function() {
                _deleteUser(backendUrl, u.id, u.username);
            });

            tr.innerHTML =
                '<td>' + u.id + '</td>' +
                '<td>' + _escHtml(u.username) + '</td>' +
                '<td' + (nameTooltip ? ' title="' + nameTooltip + '"' : '') + '>' + _escHtml(displayName) + '</td>' +
                '<td><span class="badge admin-role-badge role-' + u.role + '">' + u.role + '</span></td>' +
                '<td>' + (u.allowed_ip || '-') + '</td>' +
                '<td' + (u.last_login_at ? ' title="' + _escHtml(u.last_login_at) + '"' : '') + '>' + lastLogin + '</td>' +
                '<td>' + (u.created_at || '-') + '</td>';
            var actionsTd = document.createElement('td');
            actionsTd.className = 'admin-users-actions';
            actionsTd.appendChild(editBtn);
            actionsTd.appendChild(delBtn);
            tr.appendChild(actionsTd);
            tbody.appendChild(tr);
        });
    } catch (e) {
        tbody.innerHTML = '<tr><td colspan="8">Failed to load users</td></tr>';
    }
}

function _formatLastLogin(iso) {
    if (!iso) return '-';
    // SQLite datetime('now') → "YYYY-MM-DD HH:MM:SS" (UTC)
    var m = /^(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2})/.exec(iso);
    return m ? (m[1] + ' ' + m[2]) : iso;
}

function _addUserModal(backendUrl) {
    var existing = document.getElementById('admin-add-user-overlay');
    if (existing) existing.remove();

    var overlay = document.createElement('div');
    overlay.id = 'admin-add-user-overlay';
    overlay.className = 'admin-modal-overlay';
    overlay.innerHTML =
        '<div class="admin-modal">' +
            '<h3>사용자 추가</h3>' +
            // 오류는 모달 안에서 보여준다 — #admin-notice 는 오버레이 뒤에 가려 보이지 않는다
            '<div class="admin-settings-notice notice-error" id="admin-new-user-error" style="display:none"></div>' +
            '<div class="admin-field" style="margin-bottom:12px">' +
                '<label class="admin-field-label">Username <span style="font-weight:normal;opacity:.6">(사번, 필수)</span></label>' +
                '<input type="text" class="form-input admin-input" id="admin-new-user-name" autocomplete="off">' +
            '</div>' +
            '<div class="admin-field" style="margin-bottom:12px">' +
                '<label class="admin-field-label">Password <span style="font-weight:normal;opacity:.6">(필수)</span></label>' +
                '<input type="password" class="form-input admin-input" id="admin-new-user-pw" autocomplete="new-password">' +
            '</div>' +
            '<div class="admin-field" style="margin-bottom:12px">' +
                '<label class="admin-field-label">이름 <span style="font-weight:normal;opacity:.6">(선택, 표시용)</span></label>' +
                '<input type="text" class="form-input admin-input" id="admin-new-user-displayname">' +
            '</div>' +
            '<div class="admin-field" style="margin-bottom:12px">' +
                '<label class="admin-field-label">설명 <span style="font-weight:normal;opacity:.6">(선택, 부서·비고)</span></label>' +
                '<input type="text" class="form-input admin-input" id="admin-new-user-desc">' +
            '</div>' +
            '<div class="admin-field" style="margin-bottom:12px">' +
                '<label class="admin-field-label">Role</label>' +
                '<select class="form-select admin-select" id="admin-new-user-role">' +
                    '<option value="viewer">viewer</option>' +
                    '<option value="editor">editor</option>' +
                    '<option value="admin">admin</option>' +
                '</select>' +
            '</div>' +
            '<div class="admin-field" style="margin-bottom:16px">' +
                '<label class="admin-field-label">허용 IP <span style="font-weight:normal;opacity:.6">(비워두면 제한 없음)</span></label>' +
                '<input type="text" class="form-input admin-input" id="admin-new-user-ip">' +
            '</div>' +
            '<div style="display:flex;gap:8px;justify-content:flex-end">' +
                '<button class="btn btn-secondary admin-btn admin-btn-reset" id="admin-new-user-cancel">Cancel</button>' +
                '<button class="btn btn-primary admin-btn admin-btn-save" id="admin-new-user-save">추가</button>' +
            '</div>' +
        '</div>';

    document.body.appendChild(overlay);

    // Escape 는 document 에 건다 — 포커스가 모달 밖에 있어도 닫히도록
    function onEscape(e) { if (e.key === 'Escape') close(); }
    function close() {
        document.removeEventListener('keydown', onEscape);
        overlay.remove();
    }
    document.addEventListener('keydown', onEscape);

    document.getElementById('admin-new-user-cancel').addEventListener('click', close);
    overlay.addEventListener('click', function(e) { if (e.target === overlay) close(); });

    document.getElementById('admin-new-user-save').addEventListener('click', function() {
        _submitNewUser(backendUrl, close);
    });
    // 인라인 폼에 있던 Enter 제출 유지 (모달 안에 포커스가 있을 때만)
    overlay.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') _submitNewUser(backendUrl, close);
    });

    document.getElementById('admin-new-user-name').focus();
}

async function _submitNewUser(backendUrl, close) {
    var errEl = document.getElementById('admin-new-user-error');
    function showErr(msg) {
        if (!errEl) return;
        errEl.textContent = msg;
        errEl.style.display = 'block';
    }

    var username = document.getElementById('admin-new-user-name').value.trim();
    var password = document.getElementById('admin-new-user-pw').value;
    var role = document.getElementById('admin-new-user-role').value;
    var allowed_ip = document.getElementById('admin-new-user-ip').value.trim();
    var displayName = document.getElementById('admin-new-user-displayname').value.trim();
    var description = document.getElementById('admin-new-user-desc').value.trim();

    if (!username || !password) {
        showErr('Username 과 Password 는 필수입니다.');
        return;
    }

    try {
        var r = await fetch(backendUrl + '/api/auth/users', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({
                username: username, password: password, role: role, allowed_ip: allowed_ip,
                name: displayName || null, description: description || null
            })
        });
        if (r.ok) {
            close();
            _loadUsersTable(backendUrl);
            _showNotice('ok', '✓ 사용자가 추가되었습니다: ' + _escHtml(username));
        } else {
            var err = await r.json();
            showErr('✗ ' + (err.detail || 'Failed to add user'));
        }
    } catch (e) {
        showErr('✗ 서버 오류');
    }
}

function _editUserInline(backendUrl, u) {
    var existing = document.getElementById('admin-edit-user-overlay');
    if (existing) existing.remove();

    var currentName = u.username;
    var currentRole = u.role;
    var currentIp = u.allowed_ip || '';
    var currentDisplayName = u.name || '';
    var currentDesc = u.description || '';

    var overlay = document.createElement('div');
    overlay.id = 'admin-edit-user-overlay';
    overlay.className = 'admin-modal-overlay';
    overlay.innerHTML =
        '<div class="admin-modal">' +
            '<h3>Edit User: ' + _escHtml(currentName) + '</h3>' +
            // 오류는 모달 안에서 보여준다 — #admin-notice 는 오버레이 뒤에 가려 보이지 않는다
            '<div class="admin-settings-notice notice-error" id="admin-edit-user-error" style="display:none"></div>' +
            '<div class="admin-field" style="margin-bottom:12px">' +
                '<label class="admin-field-label">이름 <span style="font-weight:normal;opacity:.6">(선택, 표시용)</span></label>' +
                '<input type="text" class="form-input admin-input" id="admin-edit-displayname" value="' + _escHtml(currentDisplayName) + '">' +
            '</div>' +
            '<div class="admin-field" style="margin-bottom:12px">' +
                '<label class="admin-field-label">설명 <span style="font-weight:normal;opacity:.6">(선택, 부서·비고)</span></label>' +
                '<input type="text" class="form-input admin-input" id="admin-edit-desc" value="' + _escHtml(currentDesc) + '">' +
            '</div>' +
            '<div class="admin-field" style="margin-bottom:12px">' +
                '<label class="admin-field-label">New Password <span style="font-weight:normal;opacity:.6">(leave empty to keep)</span></label>' +
                '<input type="password" class="form-input admin-input" id="admin-edit-pw" autocomplete="new-password">' +
            '</div>' +
            '<div class="admin-field" style="margin-bottom:12px">' +
                '<label class="admin-field-label">Role</label>' +
                '<select class="form-select admin-select" id="admin-edit-role">' +
                    '<option value="viewer"' + (currentRole === 'viewer' ? ' selected' : '') + '>viewer</option>' +
                    '<option value="editor"' + (currentRole === 'editor' ? ' selected' : '') + '>editor</option>' +
                    '<option value="admin"' + (currentRole === 'admin' ? ' selected' : '') + '>admin</option>' +
                '</select>' +
            '</div>' +
            '<div class="admin-field" style="margin-bottom:16px">' +
                '<label class="admin-field-label">허용 IP <span style="font-weight:normal;opacity:.6">(비워두면 제한 없음)</span></label>' +
                '<input type="text" class="form-input admin-input" id="admin-edit-ip" value="' + _escHtml(currentIp) + '">' +
            '</div>' +
            '<div style="display:flex;gap:8px;justify-content:flex-end">' +
                '<button class="btn btn-secondary admin-btn admin-btn-reset" id="admin-edit-cancel">Cancel</button>' +
                '<button class="btn btn-primary admin-btn admin-btn-save" id="admin-edit-save">Save</button>' +
            '</div>' +
        '</div>';

    document.body.appendChild(overlay);

    // Escape 는 document 에 건다 — 포커스가 모달 밖에 있어도 닫히도록
    function onEscape(e) { if (e.key === 'Escape') close(); }
    function close() {
        document.removeEventListener('keydown', onEscape);
        overlay.remove();
    }
    document.addEventListener('keydown', onEscape);

    document.getElementById('admin-edit-cancel').addEventListener('click', close);
    overlay.addEventListener('click', function(e) { if (e.target === overlay) close(); });

    function showErr(msg) {
        var errEl = document.getElementById('admin-edit-user-error');
        if (!errEl) return;
        errEl.textContent = msg;
        errEl.style.display = 'block';
    }

    document.getElementById('admin-edit-save').addEventListener('click', function() {
        var newPw = document.getElementById('admin-edit-pw').value;
        var newRole = document.getElementById('admin-edit-role').value;
        var newIp = document.getElementById('admin-edit-ip').value.trim();
        var newDisplayName = document.getElementById('admin-edit-displayname').value.trim();
        var newDesc = document.getElementById('admin-edit-desc').value.trim();
        var body = {};
        if (newPw) body.password = newPw;
        if (newRole !== currentRole) body.role = newRole;
        if (newIp !== currentIp) body.allowed_ip = newIp;
        if (newDisplayName !== currentDisplayName) body.name = newDisplayName;
        if (newDesc !== currentDesc) body.description = newDesc;
        if (Object.keys(body).length === 0) { close(); return; }

        fetch(backendUrl + '/api/auth/users/' + u.id, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify(body)
        }).then(function(r) {
            if (r.ok) {
                close();
                _loadUsersTable(backendUrl);
                _showNotice('ok', '✓ 사용자가 수정되었습니다.');
            } else {
                r.json().then(function(err) { showErr('✗ ' + (err.detail || 'Failed')); });
            }
        }).catch(function() { showErr('✗ 서버 오류'); });
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
        // 전용 호스트에 렌더한다. area(#admin-content-area)는 섹션이 바뀌어도
        // 살아남는 영구 컨테이너라, 직접 넘기면 analytics.js 의 자동 갱신 중단
        // 가드(document.body.contains)가 영영 발동하지 못한다.
        area.innerHTML = '<div id="admin-dashboard-host"></div>';
        renderAnalyticsDashboard(document.getElementById('admin-dashboard-host'));
    } else {
        area.innerHTML = '<div class="admin-section"><p>analytics.js가 로드되지 않았습니다.</p></div>';
    }
}
