/* ===================================
   문서 편집기 모듈
   Toast UI Editor 기반 WYSIWYG 편집기
   =================================== */

// 편집기 상태 관리
const EditorState = {
    isOpen: false,
    isModified: false,
    currentFile: null,
    originalContent: null,
    editor: null,
    autoSaveTimer: null
};

/**
 * 편집기 초기화
 */
function initEditor() {
    // 편집 기능이 비활성화된 경우 종료
    if (!EDITOR_CONFIG.enabled) {
        return;
    }

    // 편집 버튼 생성
    createEditButton();

    // 편집기 모달 생성
    createEditorModal();

    // 이벤트 리스너 등록
    setupEditorEventListeners();
}

/**
 * 편집 버튼 생성 (h1 제목 옆에 인라인으로 삽입)
 */
function createEditButton() {
    // 버튼은 문서 로드 시 동적으로 h1에 삽입됨
    // 여기서는 아무것도 하지 않음
}

/**
 * 편집기 모달 생성
 */
function createEditorModal() {
    const modal = document.createElement('div');
    modal.id = 'editor-modal';
    modal.className = 'editor-modal';

    modal.innerHTML = `
        <div class="editor-container">
            <div class="editor-header">
                <div class="editor-title">
                    <h3>Document Editor</h3>
                    <span class="doc-path" id="editor-doc-path"></span>
                </div>
                <div class="editor-actions">
                    <button class="editor-fullscreen-btn" id="editor-fullscreen" title="Fullscreen">
                        <span class="icon"></span>
                    </button>
                    <button class="editor-cancel-btn" id="editor-cancel">
                        Cancel
                    </button>
                    <button class="btn btn-primary editor-save-btn" id="editor-save">
                        <span class="icon"></span>
                        Save
                    </button>
                    <button class="editor-close-btn" id="editor-close">&times;</button>
                </div>
            </div>
            <div class="editor-body">
                <div id="toast-editor"></div>
            </div>
            <div class="editor-footer">
                <div class="editor-status">
                    <span class="status-indicator" id="editor-status-indicator"></span>
                    <span id="editor-status-text">Ready</span>
                </div>
                <div class="editor-autosave" id="editor-autosave-info"></div>
            </div>
        </div>
    `;

    document.body.appendChild(modal);

    // 확인 다이얼로그 생성
    createConfirmDialog();

    // 토스트 알림 컨테이너 생성
    createToastContainer();
}

/**
 * 로그인 필요 UI 생성 (계정관리 연동 대비)
 */
function createLoginRequiredUI() {
    const loginUI = document.createElement('div');
    loginUI.id = 'editor-login-required';
    loginUI.className = 'editor-login-required';
    loginUI.style.display = 'none';

    loginUI.innerHTML = `
        <div class="lock-icon"></div>
        <h4>Login Required</h4>
        <p>You need to log in to edit documents.<br>Please sign in with your account.</p>
        <button class="editor-login-btn" id="editor-login-btn">
            Sign In
        </button>
    `;

    document.body.appendChild(loginUI);
}

/**
 * 확인 다이얼로그 생성
 */
function createConfirmDialog() {
    const dialog = document.createElement('div');
    dialog.id = 'editor-confirm-dialog';
    dialog.className = 'editor-confirm-dialog';

    dialog.innerHTML = `
        <div class="editor-confirm-content">
            <h4 id="confirm-title">Unsaved Changes</h4>
            <p id="confirm-message">You have unsaved changes. Are you sure you want to close?</p>
            <div class="editor-confirm-actions">
                <button class="confirm-no" id="confirm-no">Cancel</button>
                <button class="confirm-yes" id="confirm-yes">Discard</button>
            </div>
        </div>
    `;

    document.body.appendChild(dialog);
}

/**
 * 토스트 알림 컨테이너 생성 (공용 showToast()로 이관 — no-op)
 */
function createToastContainer() {
}

/**
 * 이벤트 리스너 설정
 */
function setupEditorEventListeners() {
    // 전체화면 토글
    document.getElementById('editor-fullscreen').addEventListener('click', function() {
        var container = document.querySelector('.editor-container');
        container.classList.toggle('fullscreen');
        this.title = container.classList.contains('fullscreen') ? 'Exit Fullscreen' : 'Fullscreen';
        // Monaco 레이아웃 재계산
        if (EditorState.editor && EditorState.editor.layout) {
            setTimeout(function() { EditorState.editor.layout(); }, 100);
        }
    });

    // 저장 버튼
    document.getElementById('editor-save').addEventListener('click', function() {
        saveDocument();
    });

    // 취소 버튼
    document.getElementById('editor-cancel').addEventListener('click', function() {
        closeEditorWithConfirm();
    });

    // 닫기 버튼
    document.getElementById('editor-close').addEventListener('click', function() {
        closeEditorWithConfirm();
    });

    // 모달 외부 클릭 시 닫기
    document.getElementById('editor-modal').addEventListener('click', function(e) {
        if (e.target === this) {
            closeEditorWithConfirm();
        }
    });

    // ESC 키: 전체화면 해제 → 에디터 닫기
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && EditorState.isOpen) {
            var container = document.querySelector('.editor-container');
            if (container && container.classList.contains('fullscreen')) {
                container.classList.remove('fullscreen');
                document.getElementById('editor-fullscreen').title = 'Fullscreen';
                return;
            }
            closeEditorWithConfirm();
        }
        // Ctrl+S로 저장
        if (e.ctrlKey && e.key === 's' && EditorState.isOpen) {
            e.preventDefault();
            saveDocument();
        }
    });

    // 확인 다이얼로그 버튼
    document.getElementById('confirm-yes').addEventListener('click', function() {
        hideConfirmDialog();
        closeEditor(true);
    });

    document.getElementById('confirm-no').addEventListener('click', function() {
        hideConfirmDialog();
    });
}

/**
 * 편집기 열기
 */
async function openEditor() {
    const currentPage = AppState.currentPage;

    if (!currentPage) {
        showToast('No document loaded', 'error');
        return;
    }

    // 인증 필요 시 체크
    if (EDITOR_CONFIG.requireAuth && typeof requireAdmin === 'function') {
        requireAdmin(function() { _openEditorInner(); });
        return;
    }
    _openEditorInner();
}

async function _openEditorInner() {
    const currentPage = AppState.currentPage;
    if (!currentPage) {
        showToast('No document loaded', 'error');
        return;
    }

    // 현재 문서 경로 설정
    EditorState.currentFile = currentPage;
    document.getElementById('editor-doc-path').textContent = currentPage;

    // 모달 표시
    document.getElementById('editor-modal').classList.add('active');
    EditorState.isOpen = true;

    // 문서 내용 로드
    try {
        const response = await fetch(currentPage + '?t=' + Date.now());
        if (!response.ok) throw new Error('Failed to load document');

        const content = await response.text();
        EditorState.originalContent = content;

        // Toast UI Editor 초기화
        initToastEditor(content);

        updateEditorStatus('Ready', false);

        // 자동 저장 타이머 시작
        if (EDITOR_CONFIG.autoSaveInterval > 0) {
            startAutoSave();
        }

    } catch (error) {
        console.error('Error loading document:', error);
        showToast('Failed to load document', 'error');
        closeEditor(true);
    }
}

/**
 * Monaco 에디터 초기화
 */
function initToastEditor(content) {
    const editorContainer = document.getElementById('toast-editor');
    editorContainer.innerHTML = `
        <div class="editor-loading-overlay" id="editor-loading">
            <div class="loading-spinner"></div>
            <div class="loading-text">Loading editor...</div>
        </div>
        <div class="monaco-split-container">
            <div class="monaco-editor-pane">
                <div class="pane-header">HTML Source</div>
                <div id="monaco-editor"></div>
            </div>
            <div class="monaco-split-handle" id="monaco-split-handle"></div>
            <div class="monaco-preview-pane">
                <div class="pane-header">Preview</div>
                <div id="monaco-preview" class="main-content"></div>
            </div>
        </div>
    `;

    // 분할 리사이즈 핸들 초기화
    initSplitResize();

    // Monaco가 로드되었는지 확인
    if (typeof monaco === 'undefined') {
        loadMonaco().then(() => {
            createEditorInstance(content);
            hideEditorLoading();
        }).catch(err => {
            console.error('Failed to load Monaco:', err);
            createFallbackEditor(content);
            hideEditorLoading();
        });
    } else {
        createEditorInstance(content);
        hideEditorLoading();
    }
}

/**
 * 에디터 로딩 오버레이 숨김
 */
function hideEditorLoading() {
    var overlay = document.getElementById('editor-loading');
    if (overlay) {
        overlay.style.opacity = '0';
        setTimeout(function() { overlay.remove(); }, 300);
    }
}

/**
 * 분할 패널 리사이즈 핸들
 */
function initSplitResize() {
    var handle = document.getElementById('monaco-split-handle');
    var container = handle ? handle.parentElement : null;
    if (!handle || !container) return;

    var editorPane = container.querySelector('.monaco-editor-pane');
    var previewPane = container.querySelector('.monaco-preview-pane');
    var isDragging = false;

    handle.addEventListener('mousedown', function(e) {
        isDragging = true;
        document.body.style.cursor = 'col-resize';
        document.body.classList.add('resizing');
        e.preventDefault();
    });

    document.addEventListener('mousemove', function(e) {
        if (!isDragging) return;
        var rect = container.getBoundingClientRect();
        var offset = e.clientX - rect.left;
        var total = rect.width;
        var ratio = Math.max(0.2, Math.min(0.8, offset / total));

        editorPane.style.flex = 'none';
        editorPane.style.width = (ratio * 100) + '%';
        previewPane.style.flex = 'none';
        previewPane.style.width = ((1 - ratio) * 100) + '%';
    });

    document.addEventListener('mouseup', function() {
        if (isDragging) {
            isDragging = false;
            document.body.style.cursor = '';
            document.body.classList.remove('resizing');
        }
    });

    // 더블클릭으로 균등 분할 복원
    handle.addEventListener('dblclick', function() {
        editorPane.style.flex = '1';
        editorPane.style.width = '';
        previewPane.style.flex = '1';
        previewPane.style.width = '';
    });
}

/**
 * Monaco Editor 로컬 로드
 */
function loadMonaco() {
    return new Promise((resolve, reject) => {
        const loaderScript = document.createElement('script');
        loaderScript.src = 'js/monaco-editor/vs/loader.js';
        loaderScript.onload = function() {
            require.config({ paths: { vs: 'js/monaco-editor/vs' } });
            require(['vs/editor/editor.main'], resolve);
        };
        loaderScript.onerror = reject;
        document.head.appendChild(loaderScript);
    });
}

/**
 * Monaco 에디터 인스턴스 생성
 */
function createEditorInstance(content) {
    const editorElement = document.getElementById('monaco-editor');
    const previewElement = document.getElementById('monaco-preview');

    // 미리보기용 baseDir (이미지 상대 경로 해결)
    var baseDir = '';
    if (EditorState.currentFile) {
        var idx = EditorState.currentFile.lastIndexOf('/');
        if (idx >= 0) baseDir = EditorState.currentFile.substring(0, idx + 1);
    }

    // 미리보기 초기화
    previewElement.innerHTML = (typeof resolveRelativePaths === 'function' && baseDir)
        ? resolveRelativePaths(content, baseDir) : content;

    // Monaco 에디터 생성
    EditorState.editor = monaco.editor.create(editorElement, {
        value: content,
        language: 'html',
        theme: 'vs',
        fontSize: 14,
        lineNumbers: 'on',
        minimap: { enabled: false },
        wordWrap: 'on',
        automaticLayout: true,
        scrollBeyondLastLine: false,
        tabSize: 2
    });

    // 변경 감지 및 미리보기 업데이트
    EditorState.editor.onDidChangeModelContent(function() {
        EditorState.isModified = true;
        updateEditorStatus('Modified', true);
        // 미리보기 업데이트 (디바운스)
        clearTimeout(EditorState.previewTimer);
        EditorState.previewTimer = setTimeout(function() {
            var val = EditorState.editor.getValue();
            previewElement.innerHTML = (typeof resolveRelativePaths === 'function' && baseDir)
                ? resolveRelativePaths(val, baseDir) : val;
        }, 300);
    });

    // 커서 위치 변경 시 해당 요소 하이라이트
    EditorState.editor.onDidChangeCursorPosition(function(e) {
        highlightElementAtCursor(e.position, previewElement);
    });

    // 미리보기 클릭 시 소스 위치로 이동
    previewElement.addEventListener('click', function(e) {
        var target = e.target.closest('h1,h2,h3,h4,h5,h6,p,li,td,th,tr,table,div,span,a,img,ul,ol,strong,em');
        if (target) {
            navigateToSource(target);
        }
    });
}

/**
 * 커서 위치의 요소를 미리보기에서 하이라이트
 */
function highlightElementAtCursor(position, previewElement) {
    // 기존 하이라이트 제거
    const prevHighlight = previewElement.querySelector('.editor-highlight');
    if (prevHighlight) {
        prevHighlight.classList.remove('editor-highlight');
    }

    const content = EditorState.editor.getValue();
    const lines = content.split('\n');

    // 커서 위치까지의 텍스트
    let textBeforeCursor = '';
    for (let i = 0; i < position.lineNumber - 1; i++) {
        textBeforeCursor += lines[i] + '\n';
    }
    textBeforeCursor += lines[position.lineNumber - 1].substring(0, position.column - 1);

    // 커서 위치에서 가장 가까운 ID 또는 태그 찾기
    const idMatch = textBeforeCursor.match(/id=["']([^"']+)["'][^>]*$/i);
    if (idMatch) {
        const element = previewElement.querySelector('#' + CSS.escape(idMatch[1]));
        if (element) {
            element.classList.add('editor-highlight');
            element.scrollIntoView({ behavior: 'smooth', block: 'center' });
            return;
        }
    }

    // ID가 없으면 태그와 내용으로 찾기
    const tagMatches = textBeforeCursor.match(/<(h[1-6]|p|li|td|th|tr|table|div|span|a|img|ul|ol)[^>]*>([^<]*)?$/i);
    if (tagMatches) {
        const tagName = tagMatches[1].toLowerCase();
        const textContent = tagMatches[2] ? tagMatches[2].trim() : '';

        // 해당 태그들 중 텍스트가 일치하는 요소 찾기
        const elements = previewElement.querySelectorAll(tagName);
        for (const el of elements) {
            if (textContent && el.textContent.trim().startsWith(textContent)) {
                el.classList.add('editor-highlight');
                el.scrollIntoView({ behavior: 'smooth', block: 'center' });
                return;
            }
        }

        // 텍스트 매칭 실패 시 순서로 찾기 (몇 번째 태그인지)
        const allTagsBefore = textBeforeCursor.match(new RegExp('<' + tagName + '[^>]*>', 'gi')) || [];
        const index = allTagsBefore.length - 1;
        if (elements[index]) {
            elements[index].classList.add('editor-highlight');
            elements[index].scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }
}

/**
 * 미리보기 요소 클릭 → HTML 소스 해당 위치로 이동
 */
function navigateToSource(element) {
    if (!EditorState.editor) return;

    var source = EditorState.editor.getValue();
    var tagName = element.tagName.toLowerCase();
    var text = element.textContent.trim().substring(0, 60);
    var id = element.id;
    var line = 0;

    // 1) ID로 찾기 (가장 정확)
    if (id) {
        var idPattern = new RegExp('id=["\']' + id.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '["\']');
        var lines = source.split('\n');
        for (var i = 0; i < lines.length; i++) {
            if (idPattern.test(lines[i])) {
                line = i + 1;
                break;
            }
        }
    }

    // 2) 태그 + 텍스트 내용으로 찾기
    if (!line && text) {
        var escaped = text.substring(0, 30).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        var textPattern = new RegExp('<' + tagName + '[^>]*>[^<]*' + escaped);
        var lines = source.split('\n');
        for (var i = 0; i < lines.length; i++) {
            if (textPattern.test(lines[i])) {
                line = i + 1;
                break;
            }
        }
    }

    // 3) 순서 기반 (미리보기에서 몇 번째 태그인지)
    if (!line) {
        var previewElement = document.getElementById('monaco-preview');
        var allElements = previewElement.querySelectorAll(tagName);
        var index = Array.from(allElements).indexOf(element);
        if (index >= 0) {
            var count = 0;
            var tagPattern = new RegExp('<' + tagName + '[\\s>]', 'i');
            var lines = source.split('\n');
            for (var i = 0; i < lines.length; i++) {
                if (tagPattern.test(lines[i])) {
                    if (count === index) {
                        line = i + 1;
                        break;
                    }
                    count++;
                }
            }
        }
    }

    if (line) {
        EditorState.editor.revealLineInCenter(line);
        EditorState.editor.setPosition({ lineNumber: line, column: 1 });
        EditorState.editor.focus();

        // 미리보기 하이라이트
        var prev = document.querySelector('#monaco-preview .editor-highlight');
        if (prev) prev.classList.remove('editor-highlight');
        element.classList.add('editor-highlight');
    }
}

/**
 * 폴백 에디터 (textarea 기반)
 */
function createFallbackEditor(content) {
    const container = document.getElementById('toast-editor');
    container.innerHTML = `
        <textarea id="fallback-editor" style="width: 100%; height: 100%; padding: 20px;
            font-family: 'Consolas', monospace; font-size: 14px; line-height: 1.6;
            border: none; resize: none; outline: none;">${escapeHtml(content)}</textarea>
    `;

    const textarea = document.getElementById('fallback-editor');
    textarea.addEventListener('input', function() {
        EditorState.isModified = true;
        updateEditorStatus('Modified', true);
    });

    // 폴백 에디터 객체
    EditorState.editor = {
        getValue: function() {
            return textarea.value;
        },
        dispose: function() {}
    };
}

/**
 * HTML 이스케이프
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * 편집기 상태 업데이트
 */
function updateEditorStatus(text, isModified) {
    const indicator = document.getElementById('editor-status-indicator');
    const statusText = document.getElementById('editor-status-text');

    statusText.textContent = text;

    if (isModified) {
        indicator.className = 'status-indicator modified';
    } else {
        indicator.className = 'status-indicator';
    }
}

/**
 * 자동 저장 시작
 */
function startAutoSave() {
    const interval = EDITOR_CONFIG.autoSaveInterval;

    document.getElementById('editor-autosave-info').textContent =
        `Auto-save: every ${interval / 1000}s`;

    EditorState.autoSaveTimer = setInterval(function() {
        if (EditorState.isModified) {
            saveDocument(true); // silent save
        }
    }, interval);
}

/**
 * 자동 저장 중지
 */
function stopAutoSave() {
    if (EditorState.autoSaveTimer) {
        clearInterval(EditorState.autoSaveTimer);
        EditorState.autoSaveTimer = null;
    }
}

/**
 * 문서 저장
 */
async function saveDocument(silent = false) {
    if (!EditorState.editor) return;

    const content = EditorState.editor.getValue();
    const filePath = EditorState.currentFile;

    updateEditorStatus('Saving...', true);
    document.getElementById('editor-status-indicator').classList.add('saving');

    try {
        const response = await fetch(`${EDITOR_CONFIG.backendUrl}/api/save-document`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify({
                path: filePath,
                content: content,
                createBackup: EDITOR_CONFIG.createBackup
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Save failed');
        }

        EditorState.isModified = false;
        EditorState.originalContent = content;
        updateEditorStatus('Saved', false);

        if (!silent) {
            showToast('Document saved successfully', 'success');
        }

        // 저장 후 콘텐츠 영역 새로고침
        if (typeof loadContent === 'function') {
            loadContent(filePath);
        }

        // 인덱스 상태 갱신 (파일 mtime 변경으로 outdated 표시)
        if (typeof checkIndexStatus === 'function') {
            checkIndexStatus();
        }

    } catch (error) {
        console.error('Error saving document:', error);
        updateEditorStatus('Save failed', true);

        if (!silent) {
            showToast(`Failed to save: ${error.message}`, 'error');
        }
    }

    document.getElementById('editor-status-indicator').classList.remove('saving');
}

/**
 * 확인 후 편집기 닫기
 */
function closeEditorWithConfirm() {
    if (EditorState.isModified) {
        showConfirmDialog(
            'Unsaved Changes',
            'You have unsaved changes. Are you sure you want to close without saving?'
        );
    } else {
        closeEditor(true);
    }
}

/**
 * 편집기 닫기
 */
function closeEditor(force = false) {
    if (!force && EditorState.isModified) {
        return;
    }

    // 자동 저장 중지
    stopAutoSave();

    // 모달 숨김
    document.getElementById('editor-modal').classList.remove('active');

    // 상태 초기화
    EditorState.isOpen = false;
    EditorState.isModified = false;
    EditorState.currentFile = null;
    EditorState.originalContent = null;

    // Monaco 인스턴스 정리
    if (EditorState.editor && EditorState.editor.dispose) {
        EditorState.editor.dispose();
    }
    EditorState.editor = null;
    EditorState.previewTimer = null;
}

/**
 * 확인 다이얼로그 표시
 */
function showConfirmDialog(title, message) {
    document.getElementById('confirm-title').textContent = title;
    document.getElementById('confirm-message').textContent = message;
    document.getElementById('editor-confirm-dialog').classList.add('active');
}

/**
 * 확인 다이얼로그 숨김
 */
function hideConfirmDialog() {
    document.getElementById('editor-confirm-dialog').classList.remove('active');
}

/**
 * 로그인 상태 확인
 */
function isUserLoggedIn() {
    return typeof AuthState !== 'undefined' && AuthState.user && AuthState.user.role === 'admin';
}

/**
 * 편집 버튼 표시/숨김 (문서 로드 시 호출)
 * 상단 네비게이션의 Edit 버튼 표시/숨김 제어
 */
function updateEditButtonVisibility() {
    const navEditItem = document.getElementById('nav-edit-item');
    if (!navEditItem) return;

    // 편집기 비활성화 상태면 숨김
    if (!EDITOR_CONFIG.enabled) {
        navEditItem.style.display = 'none';
        return;
    }

    const currentPage = AppState.currentPage;

    // home.html, about.html 등 기본 페이지는 편집 비활성화
    const nonEditablePages = ['home.html', 'about.html'];
    const isEditable = currentPage &&
        !nonEditablePages.some(page => currentPage.includes(page));

    navEditItem.style.display = isEditable ? '' : 'none';
}

// DOM 로드 시 편집기 초기화
document.addEventListener('DOMContentLoaded', function() {
    initEditor();
});
