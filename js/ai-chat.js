/* ===================================
   AI 채팅 기능
   =================================== */

// 채팅 상태 관리
var AIChatState = {
    isOpen: false,
    isLoading: false,
    isExpanded: false,
    messages: [],
    currentSection: null,  // 현재 활성 섹션 정보
    conversationId: null   // 멀티턴 대화 세션 ID
};

/**
 * AI 채팅 초기화
 */
function initAIChat() {
    var fab = document.getElementById('ai-chat-fab');
    var container = document.getElementById('ai-chat-container');
    var input = document.getElementById('ai-chat-input');
    var sendBtn = document.getElementById('ai-chat-send');
    var clearBtn = document.getElementById('ai-chat-clear');

    if (!fab || !container) return;

    // AI 챗봇 비활성화 시 아이콘 숨김
    if (typeof AI_CONFIG !== 'undefined' && AI_CONFIG.enabled === false) {
        fab.style.display = 'none';
        container.style.display = 'none';
        return;
    }

    // 플로팅 버튼 클릭
    fab.addEventListener('click', function() {
        toggleAIChat();
    });

    // FAB 위치를 우측 패널 기준으로 조정
    initFabPosition(fab);

    // 스크롤 시 FAB 반투명 처리
    initFabScrollFade(fab);

    // 전송 버튼 클릭
    if (sendBtn) {
        sendBtn.addEventListener('click', function() {
            sendMessage();
        });
    }

    // 입력창 엔터키
    if (input) {
        input.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });

        // 입력창 자동 높이 조절
        input.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = Math.min(this.scrollHeight, 100) + 'px';
        });
    }

    // 대화 초기화 버튼
    if (clearBtn) {
        clearBtn.addEventListener('click', function() {
            clearChat();
        });
    }

    // 확장 버튼
    var expandBtn = document.getElementById('ai-chat-expand');
    if (expandBtn) {
        expandBtn.addEventListener('click', function() {
            toggleExpand();
        });
    }

    // 빠른 질문 버튼
    initQuickActions();

    // 브랜드명 표시
    var modelNameEl = document.getElementById('ai-model-name');
    if (modelNameEl) {
        modelNameEl.textContent = '(Powered by DE-Genie)';
    }

    // 현재 섹션 추적 시작
    initSectionTracking();

    // ESC 키로 닫기
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && AIChatState.isOpen) {
            toggleAIChat();
        }
    });

}

/**
 * 채팅창 토글
 */
function toggleAIChat() {
    var fab = document.getElementById('ai-chat-fab');
    var container = document.getElementById('ai-chat-container');
    var input = document.getElementById('ai-chat-input');

    AIChatState.isOpen = !AIChatState.isOpen;

    if (AIChatState.isOpen) {
        fab.classList.add('active');
        container.classList.add('open');
        if (input) input.focus();
    } else {
        fab.classList.remove('active');
        container.classList.remove('open');
    }
}

/**
 * 채팅창 확장/축소 토글
 */
function toggleExpand() {
    var container = document.getElementById('ai-chat-container');
    var expandBtn = document.getElementById('ai-chat-expand');

    AIChatState.isExpanded = !AIChatState.isExpanded;

    if (AIChatState.isExpanded) {
        container.classList.add('expanded');
        expandBtn.title = 'Collapse';
    } else {
        container.classList.remove('expanded');
        expandBtn.title = 'Expand';
    }

}

/**
 * 마크다운을 HTML로 변환
 * 지원: bold(**), italic(*), inline code, code block, ul, ol, table, link
 * 헤딩(#) → bold 처리 (크기/색상 변경 없음), blockquote/hr 제거
 */
function parseMarkdown(text) {
    if (!text) return '';

    // 1. 코드 블록 보호 (다른 치환에 영향받지 않도록 placeholder로 대체)
    var codeBlocks = [];
    var html = text.replace(/```[\w]*\n?([\s\S]*?)```/g, function(_, code) {
        codeBlocks.push('<pre><code>' + escapeHtml(code.trim()) + '</code></pre>');
        return '\x00CB' + (codeBlocks.length - 1) + '\x00';
    });

    // 1.5. LaTeX 수식 보호 + KaTeX 렌더링
    var mathBlocks = [];
    if (typeof katex !== 'undefined') {
        // 디스플레이 수식: $$...$$
        html = html.replace(/\$\$([\s\S]+?)\$\$/g, function(_, tex) {
            try {
                mathBlocks.push(katex.renderToString(tex.trim(), { displayMode: true, throwOnError: false }));
            } catch (e) {
                mathBlocks.push('<code>' + escapeHtml(tex.trim()) + '</code>');
            }
            return '\x00MT' + (mathBlocks.length - 1) + '\x00';
        });
        // 인라인 수식: $...$  (단, 금액 패턴 $숫자 제외)
        html = html.replace(/\$([^\$\n]+?)\$/g, function(m, tex) {
            if (/^\d/.test(tex.trim())) return m; // $100 같은 금액 패턴 스킵
            try {
                mathBlocks.push(katex.renderToString(tex.trim(), { displayMode: false, throwOnError: false }));
            } catch (e) {
                mathBlocks.push('<code>' + escapeHtml(tex.trim()) + '</code>');
            }
            return '\x00MT' + (mathBlocks.length - 1) + '\x00';
        });
    }

    // 2. 인라인 코드 보호
    var inlineCodes = [];
    html = html.replace(/`([^`\n]+)`/g, function(_, code) {
        inlineCodes.push('<code>' + escapeHtml(code) + '</code>');
        return '\x00IC' + (inlineCodes.length - 1) + '\x00';
    });

    // 3. 테이블 파싱 (| 로 감싸진 연속 라인, 2번째 줄이 구분자)
    var tableLines = [];
    var resultLines = [];
    var lines = html.split('\n');
    for (var i = 0; i < lines.length; i++) {
        var line = lines[i];
        if (/^\|.+\|$/.test(line.trim())) {
            tableLines.push(line);
        } else {
            if (tableLines.length >= 2 && /^\|[-\s:|]+\|$/.test(tableLines[1].trim())) {
                resultLines.push(renderTable(tableLines));
            } else {
                resultLines = resultLines.concat(tableLines);
            }
            tableLines = [];
            resultLines.push(line);
        }
    }
    if (tableLines.length >= 2 && /^\|[-\s:|]+\|$/.test(tableLines[1].trim())) {
        resultLines.push(renderTable(tableLines));
    } else {
        resultLines = resultLines.concat(tableLines);
    }
    html = resultLines.join('\n');

    // 4. 헤딩(#~####) → 굵게 (크기/색상 변경 없음)
    html = html.replace(/^#{1,4} (.+)$/gm, '<strong>$1</strong>');

    // 5. 굵은 글씨 **...** (__ 제외: 한국어 기술용어 오탐 방지)
    html = html.replace(/\*\*([^*\n]+)\*\*/g, '<strong>$1</strong>');

    // 6. 기울임 *...* (_ 제외: 기술 식별자 오탐 방지)
    html = html.replace(/\*([^*\n]+)\*/g, '<em>$1</em>');

    // 7. 구분선 제거
    html = html.replace(/^[-*]{3,}$/gm, '');

    // 8. 인용구 → 텍스트만 유지 (> 기호 제거)
    html = html.replace(/^> (.+)$/gm, '$1');

    // 9. 순서 없는 리스트 (- 또는 *)
    html = html.replace(/^[ \t]*[\-\*] (.+)$/gm, '\x01<li>$1</li>');
    html = html.replace(/((?:\x01<li>[^\n]*<\/li>\n?)+)/g, function(m) {
        return '<ul>' + m.replace(/\x01/g, '') + '</ul>';
    });
    html = html.replace(/\x01/g, '');

    // 10. 순서 있는 리스트 (1. 2. ...)
    html = html.replace(/^[ \t]*\d+\. (.+)$/gm, '\x02<li>$1</li>');
    html = html.replace(/((?:\x02<li>[^\n]*<\/li>\n?)+)/g, function(m) {
        return '<ol>' + m.replace(/\x02/g, '') + '</ol>';
    });
    html = html.replace(/\x02/g, '');

    // 11. 링크 [텍스트](URL)
    html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>');

    // 12. 단락 구분 (빈 줄 → <p>)
    var paragraphs = html.split(/\n\s*\n/);
    if (paragraphs.length > 1) {
        html = paragraphs.map(function(p) {
            p = p.trim();
            if (!p) return '';
            if (/^<(ul|ol|pre|table)/.test(p)) return p;
            return '<p>' + p + '</p>';
        }).filter(Boolean).join('\n');
    }

    // 13. 단일 줄바꿈 → <br>
    html = html.replace(/\n(?!<)/g, '<br>\n');
    html = html.replace(/<p><br>/g, '<p>');
    html = html.replace(/<br><\/p>/g, '</p>');

    // 14. 빈 태그 제거
    html = html.replace(/<ul>\s*<\/ul>/g, '');
    html = html.replace(/<ol>\s*<\/ol>/g, '');
    html = html.replace(/<p>\s*<\/p>/g, '');

    // 15. placeholder 복원
    html = html.replace(/\x00CB(\d+)\x00/g, function(_, i) { return codeBlocks[+i]; });
    html = html.replace(/\x00IC(\d+)\x00/g, function(_, i) { return inlineCodes[+i]; });
    html = html.replace(/\x00MT(\d+)\x00/g, function(_, i) { return mathBlocks[+i]; });

    return html;
}

/**
 * 마크다운 테이블 라인 배열 → HTML table
 */
function renderTable(lines) {
    var headers = splitTableRow(lines[0]);
    var html = '<table><thead><tr>';
    headers.forEach(function(h) { html += '<th>' + h + '</th>'; });
    html += '</tr></thead>';
    if (lines.length > 2) {
        html += '<tbody>';
        for (var i = 2; i < lines.length; i++) {
            var cells = splitTableRow(lines[i]);
            html += '<tr>';
            cells.forEach(function(c) { html += '<td>' + c + '</td>'; });
            html += '</tr>';
        }
        html += '</tbody>';
    }
    html += '</table>';
    return html;
}

/**
 * 마크다운 테이블 행 → 셀 배열 분리
 */
function splitTableRow(line) {
    return line.trim()
        .replace(/^\||\|$/g, '')
        .split('|')
        .map(function(c) { return c.trim(); });
}

/**
 * HTML 이스케이프 (코드 블록 내 특수문자 처리)
 */
function escapeHtml(text) {
    var div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * 메시지 전송
 */
async function sendMessage() {
    var input = document.getElementById('ai-chat-input');
    var message = input.value.trim();

    if (!message || AIChatState.isLoading) return;

    // 사용자 메시지 추가
    addMessage('user', message);
    input.value = '';
    input.style.height = 'auto';

    // 로딩 상태 시작
    AIChatState.isLoading = true;

    // 타이핑 인디케이터 표시
    showTypingIndicator();

    try {
        var response;

        if (AI_CONFIG.useBackend) {
            // 멀티턴 모드: 백엔드가 검색 + 쿼리 재작성 + 응답 생성 통합 처리
            response = await requestViaBackend(message);
        } else {
            // 직접 Ollama 호출 (싱글턴 — 기존 동작 유지)
            var relevantDocs = await searchRelevantDocuments(message);
            response = await requestViaOllama(message, relevantDocs);
        }

        // 타이핑 인디케이터 숨김
        hideTypingIndicator();

        // 응답 메시지 추가
        addMessage('assistant', response.answer, response.sources);

    } catch (error) {
        hideTypingIndicator();
        addMessage('error', getErrorMessage(error));
    }

    AIChatState.isLoading = false;
}

/**
 * 관련 문서 검색
 */
async function searchRelevantDocuments(query) {
    // 백엔드 사용 시 API 호출
    if (AI_CONFIG.useBackend) {
        return await searchViaBackend(query);
    }

    // 직접 검색 (로컬 인덱스 사용)
    return searchLocally(query);
}

/**
 * 백엔드 API를 통한 검색
 */
async function searchViaBackend(query) {
    try {
        var response = await fetch(AI_CONFIG.backendUrl + '/api/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({
                query: query,
                top_k: AI_CONFIG.maxSearchResults,
                search_type: AI_CONFIG.searchType || 'hybrid'
            })
        });

        if (!response.ok) {
            throw new Error('Search API error: ' + response.status);
        }

        var data = await response.json();
        return data.results.map(function(r) {
            return {
                title: r.title,
                content: r.content,
                path: r.path,
                sectionId: r.section_id || null,
                score: r.score
            };
        });
    } catch (error) {
        console.warn('Backend search failed, falling back to local:', error);
        return searchLocally(query);
    }
}

/**
 * 로컬 검색 인덱스 사용
 */
function searchLocally(query) {
    var results = [];

    if (AppState.searchIndex && AppState.searchIndex.length > 0) {
        var queryTerms = query.toLowerCase().trim()
            .split(/\s+/)
            .filter(function(term) { return term.length >= 2; });

        if (queryTerms.length > 0) {
            AppState.searchIndex.forEach(function(doc) {
                var titleLower = doc.title.toLowerCase();
                var contentLower = doc.content.toLowerCase();
                var score = 0;

                queryTerms.forEach(function(term) {
                    if (titleLower.includes(term)) score += 10;
                    if (contentLower.includes(term)) score += 1;
                });

                if (score > 0) {
                    results.push({
                        title: doc.title,
                        content: doc.content,
                        path: doc.url,
                        sectionId: doc.section_id || null,
                        score: score
                    });
                }
            });

            results.sort(function(a, b) { return b.score - a.score; });
            results = results.slice(0, AI_CONFIG.maxSearchResults);
        }
    }

    // 검색 결과가 없으면 현재 페이지 내용 사용
    if (results.length === 0) {
        var mainContent = document.getElementById('main-content');
        if (mainContent) {
            var h1 = mainContent.querySelector('h1');
            results.push({
                title: h1 ? h1.textContent.trim() : 'Current Page',
                content: mainContent.innerText.substring(0, AI_CONFIG.maxContextLength),
                path: AppState.currentPage || '',
                sectionId: null
            });
        }
    }

    return results;
}

/**
 * 백엔드 API를 통한 AI 응답 요청 (멀티턴 대화)
 * 백엔드가 검색 + 쿼리 재작성 + 응답 생성을 통합 처리
 */
async function requestViaBackend(question) {
    var payload = { question: question };
    if (AIChatState.conversationId) {
        payload.conversation_id = AIChatState.conversationId;
    }

    var controller = new AbortController();
    var timeoutId = setTimeout(function() { controller.abort(); }, 60000);

    var response = await fetch(AI_CONFIG.backendUrl + '/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(payload),
        signal: controller.signal
    });
    clearTimeout(timeoutId);

    if (!response.ok) {
        var errorBody = '';
        try { errorBody = await response.text(); } catch (e) {}
        throw new Error('API 요청 실패: ' + response.status + (errorBody ? ' - ' + errorBody : ''));
    }

    var data = await response.json();

    // 세션 ID 저장 (멀티턴 유지)
    if (data.conversation_id) {
        AIChatState.conversationId = data.conversation_id;
    }

    return {
        answer: data.answer || '',
        sources: data.sources ? data.sources.map(function(s) {
            return { title: s.title, path: s.path, sectionId: s.section_id || s.sectionId || null };
        }) : []
    };
}

/**
 * Ollama 직접 호출
 */
async function requestViaOllama(question, documents) {
    // 컨텍스트 구성
    var context = documents.map(function(doc) {
        return '[' + doc.title + ']\n' + doc.content;
    }).join('\n\n');

    if (context.length > AI_CONFIG.maxContextLength) {
        context = context.substring(0, AI_CONFIG.maxContextLength) + '...';
    }

    var prompt = AI_CONFIG.systemPrompt + '\n\n' +
        '=== 참고 문서 ===\n' + context + '\n\n' +
        '=== 질문 ===\n' + question;

    var response = await fetch(AI_CONFIG.ollamaUrl + '/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            model: AI_CONFIG.model,
            prompt: prompt,
            stream: false
        })
    });

    if (!response.ok) {
        var errorBody = '';
        try { errorBody = await response.text(); } catch (e) {}
        throw new Error('API 요청 실패: ' + response.status + (errorBody ? ' - ' + errorBody : ''));
    }

    var data = await response.json();

    return {
        answer: data.response || '',
        sources: documents.map(function(doc) {
            return { title: doc.title, path: doc.path, sectionId: doc.sectionId || null };
        })
    };
}

/**
 * 메시지 추가
 */
function addMessage(role, content, sources) {
    var messagesContainer = document.getElementById('ai-chat-messages');
    if (!messagesContainer) return;

    // 웰컴 메시지 제거
    var welcome = messagesContainer.querySelector('.ai-chat-welcome');
    if (welcome) welcome.remove();

    var messageEl = document.createElement('div');

    if (role === 'error') {
        messageEl.className = 'ai-chat-error';
        messageEl.textContent = content;
    } else {
        messageEl.className = 'ai-chat-message ' + role;

        // assistant 메시지는 마크다운 렌더링 적용
        if (role === 'assistant') {
            var contentSpan = document.createElement('span');
            contentSpan.className = 'message-content';
            contentSpan.innerHTML = parseMarkdown(content);
            messageEl.appendChild(contentSpan);
        } else {
            messageEl.textContent = content;
        }

        // 소스 추가 (assistant 메시지만)
        if (role === 'assistant' && sources && sources.length > 0) {
            var sourcesEl = document.createElement('div');
            sourcesEl.className = 'ai-chat-sources';
            sourcesEl.innerHTML = '참고: ' + sources.map(function(s) {
                if (s.path) {
                    // 섹션 ID가 있으면 해당 섹션으로 스크롤
                    if (s.sectionId) {
                        return '<a href="#" onclick="navigateToSection(\'' + s.path + '\', \'' + s.sectionId + '\'); return false;">' + s.title + '</a>';
                    }
                    return '<a href="#" onclick="loadContent(\'' + s.path + '\'); return false;">' + s.title + '</a>';
                }
                return s.title;
            }).join(', ');
            messageEl.appendChild(sourcesEl);
        }
    }

    messagesContainer.appendChild(messageEl);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;

    // 상태에 저장
    AIChatState.messages.push({ role: role, content: content });
}

/**
 * 스트리밍 메시지 요소 생성
 */
function createStreamingMessage() {
    var messagesContainer = document.getElementById('ai-chat-messages');
    if (!messagesContainer) return null;

    // 웰컴 메시지 제거
    var welcome = messagesContainer.querySelector('.ai-chat-welcome');
    if (welcome) welcome.remove();

    var messageEl = document.createElement('div');
    messageEl.className = 'ai-chat-message assistant streaming';

    var contentEl = document.createElement('span');
    contentEl.className = 'message-content';
    messageEl.appendChild(contentEl);

    // 점 3개 타이핑 인디케이터
    var cursorEl = document.createElement('span');
    cursorEl.className = 'streaming-cursor';
    cursorEl.innerHTML = '<span></span><span></span><span></span>';
    messageEl.appendChild(cursorEl);

    messagesContainer.appendChild(messageEl);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;

    return messageEl;
}

/**
 * 스트리밍 메시지 업데이트
 */
function updateStreamingMessage(messageEl, text) {
    if (!messageEl) return;

    var contentEl = messageEl.querySelector('.message-content');
    if (contentEl) {
        // 스트리밍 중에는 단순 텍스트로 표시 (박스 크기 문제 방지)
        contentEl.textContent = text;
    }

    var messagesContainer = document.getElementById('ai-chat-messages');
    if (messagesContainer) {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
}

/**
 * 스트리밍 완료 후 마무리
 */
function finalizeStreamingMessage(messageEl, sources) {
    if (!messageEl) return;

    // 커서 제거
    var cursor = messageEl.querySelector('.streaming-cursor');
    if (cursor) cursor.remove();

    messageEl.classList.remove('streaming');

    // 마크다운 렌더링 적용 (스트리밍 완료 후)
    var contentEl = messageEl.querySelector('.message-content');
    var rawText = contentEl ? contentEl.textContent : '';
    if (contentEl && rawText) {
        contentEl.innerHTML = parseMarkdown(rawText);
    }

    // 소스 추가
    if (sources && sources.length > 0) {
        var sourcesEl = document.createElement('div');
        sourcesEl.className = 'ai-chat-sources';
        sourcesEl.innerHTML = '참고: ' + sources.map(function(s) {
            if (s.path) {
                return '<a href="#" onclick="loadContent(\'' + s.path + '\'); return false;">' + s.title + '</a>';
            }
            return s.title;
        }).join(', ');
        messageEl.appendChild(sourcesEl);
    }

    // 상태에 저장
    AIChatState.messages.push({ role: 'assistant', content: rawText });
}

/**
 * 타이핑 인디케이터 표시
 */
function showTypingIndicator() {
    var messagesContainer = document.getElementById('ai-chat-messages');
    if (!messagesContainer) return;

    var typing = document.createElement('div');
    typing.className = 'ai-chat-typing';
    typing.id = 'ai-typing-indicator';
    typing.innerHTML = '<span></span><span></span><span></span>';
    messagesContainer.appendChild(typing);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

/**
 * 타이핑 인디케이터 숨김
 */
function hideTypingIndicator() {
    var typing = document.getElementById('ai-typing-indicator');
    if (typing) typing.remove();
}

/**
 * 대화 초기화
 */
function clearChat() {
    var messagesContainer = document.getElementById('ai-chat-messages');
    if (!messagesContainer) return;

    messagesContainer.innerHTML =
        '<div class="ai-chat-welcome">' +
        '    <div class="welcome-icon"></div>' +
        '    <h4>AI 어시스턴트</h4>' +
        '    <p>문서 내용에 대해 질문해보세요.<br>관련 정보를 찾아 답변해드립니다.</p>' +
        '</div>';

    AIChatState.messages = [];
    AIChatState.conversationId = null;
}

/**
 * 섹션으로 이동 (같은 페이지면 스크롤, 다른 페이지면 로드 후 스크롤)
 */
function navigateToSection(pagePath, sectionId) {
    var contentPanel = document.getElementById('content-panel');

    // 같은 페이지인 경우 스크롤만
    if (AppState.currentPage === pagePath) {
        var targetEl = document.getElementById(sectionId);
        // 분할 섹션 ID(-2, -3 등)가 없으면 원본 ID로 폴백
        if (!targetEl) {
            var baseId = sectionId.replace(/-\d+$/, '');
            targetEl = document.getElementById(baseId);
        }
        if (targetEl) {
            scrollToElementReliably(targetEl);
        }
    } else {
        // 다른 페이지인 경우 페이지 로드 후 스크롤
        // loadContent 완료 후 스크롤하기 위해 앵커 정보 저장
        window._pendingScrollToSection = sectionId;
        loadContent(pagePath);
    }
}


/**
 * 현재 섹션 추적 초기화
 */
function initSectionTracking() {
    var contentPanel = document.getElementById('content-panel');
    var sectionNav = document.getElementById('section-nav');

    if (!contentPanel) return;

    // 스크롤 이벤트로 현재 섹션 감지
    contentPanel.addEventListener('scroll', debounce(updateCurrentSection, 200));

    // 페이지 전환 시 섹션 네비게이터 변경 감지
    if (sectionNav) {
        var observer = new MutationObserver(function() {
            // 약간의 딜레이 후 섹션 업데이트 (DOM 렌더링 완료 대기)
            setTimeout(updateCurrentSection, 100);
        });
        observer.observe(sectionNav, { childList: true, subtree: true });
    }

    // 초기 섹션 업데이트
    setTimeout(updateCurrentSection, 500);
}

/**
 * 현재 활성 섹션 업데이트
 */
function updateCurrentSection() {
    var sectionNav = document.getElementById('section-nav');
    var contextEl = document.getElementById('ai-current-section');

    if (!contextEl) return;

    // 우측 목차에서 활성화된 링크 찾기
    var activeLink = sectionNav ? sectionNav.querySelector('a.active') : null;

    if (activeLink) {
        var sectionTitle = activeLink.textContent.trim();
        AIChatState.currentSection = {
            id: activeLink.getAttribute('href').replace('#', ''),
            title: sectionTitle
        };
        contextEl.textContent = sectionTitle;
        contextEl.title = sectionTitle;  // 툴팁으로 전체 제목 표시
    } else {
        // 활성 섹션이 없으면 문서 제목 사용
        var mainContent = document.getElementById('main-content');
        var h1 = mainContent ? mainContent.querySelector('h1') : null;
        if (h1) {
            AIChatState.currentSection = {
                id: null,
                title: h1.textContent.trim()
            };
            contextEl.textContent = h1.textContent.trim();
            contextEl.title = h1.textContent.trim();
        } else {
            AIChatState.currentSection = null;
            contextEl.textContent = '섹션을 선택하세요';
        }
    }
}

/**
 * 현재 섹션 콘텐츠 가져오기
 */
function getCurrentSectionContent() {
    var mainContent = document.getElementById('main-content');
    if (!mainContent) return null;

    var basePath = AppState.currentPage || '';

    // 현재 활성 섹션이 없으면 문서 전체 반환
    if (!AIChatState.currentSection || !AIChatState.currentSection.id) {
        var h1 = mainContent.querySelector('h1');
        var title = h1 ? h1.textContent.trim() : '현재 문서';
        return {
            title: title,
            content: mainContent.innerText.substring(0, AI_CONFIG.maxContextLength),
            path: basePath,
            sectionId: null
        };
    }

    // 현재 섹션 요소 찾기
    var sectionEl = document.getElementById(AIChatState.currentSection.id);
    if (!sectionEl) return null;

    // 섹션 내용 추출 (해당 헤딩부터 다음 같은 레벨 헤딩까지)
    var sectionContent = extractSectionContent(sectionEl);

    return {
        title: AIChatState.currentSection.title,
        content: sectionContent.substring(0, AI_CONFIG.maxContextLength),
        path: basePath,
        sectionId: AIChatState.currentSection.id
    };
}

/**
 * 섹션 콘텐츠 추출 (헤딩부터 다음 같은 레벨 헤딩까지)
 */
function extractSectionContent(headingEl) {
    var content = headingEl.textContent + '\n';
    var headingLevel = parseInt(headingEl.tagName.charAt(1));
    var sibling = headingEl.nextElementSibling;

    while (sibling) {
        // 같은 레벨 또는 상위 레벨 헤딩을 만나면 중단
        if (sibling.tagName && sibling.tagName.match(/^H[1-6]$/)) {
            var siblingLevel = parseInt(sibling.tagName.charAt(1));
            if (siblingLevel <= headingLevel) {
                break;
            }
        }
        content += sibling.textContent + '\n';
        sibling = sibling.nextElementSibling;
    }

    return content.trim();
}

/**
 * 디바운스 유틸리티
 */
function debounce(func, wait) {
    var timeout;
    return function() {
        var context = this, args = arguments;
        clearTimeout(timeout);
        timeout = setTimeout(function() {
            func.apply(context, args);
        }, wait);
    };
}

/**
 * 빠른 질문 버튼 초기화
 */
function initQuickActions() {
    var quickBtns = document.querySelectorAll('.ai-quick-btn');

    quickBtns.forEach(function(btn) {
        btn.addEventListener('click', function() {
            var action = this.getAttribute('data-action');
            executeQuickAction(action);
        });
    });
}

/**
 * 빠른 질문 실행 (현재 섹션 기반)
 */
async function executeQuickAction(action) {
    if (AIChatState.isLoading) return;

    // 현재 섹션 콘텐츠 가져오기
    var sectionData = getCurrentSectionContent();
    if (!sectionData) {
        addMessage('error', '섹션 내용을 가져올 수 없습니다.');
        return;
    }

    var titleText = sectionData.title;

    var prompts = {
        summarize: '"' + titleText + '" 섹션을 3-5문장으로 요약해주세요.',
        keypoints: '"' + titleText + '" 섹션의 핵심 내용을 불릿 포인트로 정리해주세요.',
        explain: '"' + titleText + '" 섹션의 내용을 비전문가도 이해할 수 있게 쉽게 설명해주세요.'
    };

    var question = prompts[action];
    if (!question) return;

    // 사용자 메시지로 표시
    addMessage('user', question);

    // 로딩 시작
    AIChatState.isLoading = true;

    // 타이핑 인디케이터 표시
    showTypingIndicator();

    try {
        var response;
        var docs = [sectionData];

        if (AI_CONFIG.useBackend) {
            // 백엔드 모드: 멀티턴 대화로 전달
            response = await requestViaBackend(question);
        } else {
            response = await requestViaOllama(question, docs);
        }

        // 타이핑 인디케이터 숨김
        hideTypingIndicator();

        // 응답 메시지 추가
        addMessage('assistant', response.answer, response.sources);

    } catch (error) {
        hideTypingIndicator();
        addMessage('error', getErrorMessage(error));
    }

    AIChatState.isLoading = false;
}

/**
 * 에러 메시지 생성
 */
function getErrorMessage(error) {
    var message = error.message || '';
    var serverUrl = AI_CONFIG.useBackend ? AI_CONFIG.backendUrl : AI_CONFIG.ollamaUrl;
    var serverName = AI_CONFIG.useBackend ? '백엔드' : 'Ollama';

    // 타임아웃
    if (error.name === 'AbortError') {
        return '응답 시간이 초과되었습니다. 다시 시도해주세요.';
    }

    // 네트워크 연결 실패
    if (error.name === 'TypeError' && message.includes('fetch')) {
        return serverName + ' 서버에 연결할 수 없습니다.\n' +
               '• 서버가 실행 중인지 확인하세요\n' +
               '• 서버 주소: ' + serverUrl;
    }

    // 네트워크 오류
    if (error.name === 'TypeError' || message.includes('network') || message.includes('Network')) {
        return serverName + ' 서버에 연결할 수 없습니다.\n' +
               '• 서버가 실행 중인지 확인하세요\n' +
               '• 서버 주소: ' + serverUrl;
    }

    // HTTP 오류
    if (message.includes('API 요청 실패')) {
        var statusMatch = message.match(/\d+/);
        var status = statusMatch ? parseInt(statusMatch[0]) : 0;

        if (status === 404) {
            if (AI_CONFIG.useBackend) {
                return 'API 엔드포인트를 찾을 수 없습니다.\n' +
                       '• 백엔드 서버가 올바르게 실행 중인지 확인하세요';
            }
            return '모델을 찾을 수 없습니다.\n' +
                   '• 모델명: ' + AI_CONFIG.model + '\n' +
                   '• "ollama pull ' + AI_CONFIG.model + '" 명령으로 설치하세요';
        }
        if (status === 500) {
            return serverName + ' 서버 오류가 발생했습니다.\n' +
                   '• 서버를 재시작해보세요';
        }
        if (status === 503) {
            return serverName + ' 서버가 일시적으로 사용 불가합니다.\n' +
                   '• 잠시 후 다시 시도하세요';
        }
    }

    // 타임아웃
    if (message.includes('timeout') || message.includes('Timeout')) {
        return '응답 시간이 초과되었습니다.\n' +
               '• 질문을 더 짧게 해보세요\n' +
               '• 서버 상태를 확인하세요';
    }

    // 기타 오류
    return 'AI 응답 중 오류가 발생했습니다:\n' + message;
}

/**
 * FAB 위치를 우측 패널 기준으로 자동 조정
 * - 패널 표시: 패널 좌측 + 16px 여백
 * - 패널 숨김: 화면 우측 24px
 * - 리사이즈에도 자동 추적
 */
function initFabPosition(fab) {
    var rightPanel = document.getElementById('right-panel');
    var container = document.getElementById('ai-chat-container');
    if (!rightPanel) return;

    function update() {
        var isHidden = rightPanel.classList.contains('hidden');
        if (isHidden) {
            fab.style.right = '24px';
            if (container) container.style.right = '24px';
        } else {
            var panelWidth = rightPanel.offsetWidth;
            var offset = panelWidth + 4 + 16; // 패널 + 리사이즈핸들 + 여백
            fab.style.right = offset + 'px';
            if (container) container.style.right = offset + 'px';
        }
    }

    // 패널 숨김/표시 감지
    new MutationObserver(update).observe(rightPanel, { attributes: true });

    // 패널 리사이즈 감지
    if (typeof ResizeObserver !== 'undefined') {
        new ResizeObserver(update).observe(rightPanel);
    }

    update();
}

/**
 * 스크롤 시 FAB 반투명 축소 처리
 * - 콘텐츠 스크롤 중 → 반투명 + 축소 (콘텐츠 가림 최소화)
 * - 스크롤 멈춤/호버 → 원래 크기 복원
 * - 채팅 열린 상태에서는 적용 안 함
 */
function initFabScrollFade(fab) {
    var contentPanel = document.getElementById('content-panel');
    if (!contentPanel) return;

    var scrollTimer;

    contentPanel.addEventListener('scroll', function() {
        if (AIChatState.isOpen) return;
        fab.classList.add('faded');
        clearTimeout(scrollTimer);
        scrollTimer = setTimeout(function() {
            fab.classList.remove('faded');
        }, 800);
    });
}

// DOM 로드 시 초기화
document.addEventListener('DOMContentLoaded', function() {
    initAIChat();
});
