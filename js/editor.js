/* ===================================
   Explorer 문서 편집기 어댑터
   EditorCore 기반 HTML 편집기
   =================================== */

// Explorer 편집기 인스턴스 (EditorCore 기반)
var _explorerEditor = null;

/**
 * 편집기 초기화
 */
function initEditor() {
    if (!EDITOR_CONFIG.enabled) return;

    _explorerEditor = EditorCore.create({
        language: 'html',
        title: 'Document Editor',
        sourceLabel: 'HTML Source',
        previewLabel: 'Preview',
        previewClass: 'main-content',
        autoSaveInterval: EDITOR_CONFIG.autoSaveInterval || 0,
        renderPreview: function (content) {
            return content;  // HTML은 그대로 주입
        },
        resolveAssets: function (content) {
            if (typeof resolveRelativePaths === 'function' && _explorerEditorBaseDir) {
                return resolveRelativePaths(content, _explorerEditorBaseDir);
            }
            return content;
        },
        onSave: async function (content) {
            var filePath = _explorerEditorFile;
            var response = await fetch(EDITOR_CONFIG.backendUrl + '/api/save-document', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({
                    path: filePath,
                    content: content,
                    createBackup: EDITOR_CONFIG.createBackup,
                }),
            });
            if (!response.ok) {
                var error = await response.json();
                throw new Error(error.detail || 'Save failed');
            }
            // 저장 후 콘텐츠 영역 새로고침
            if (typeof loadContent === 'function') {
                loadContent(filePath);
            }
            // 인덱스 상태 갱신
            if (typeof checkIndexStatus === 'function') {
                checkIndexStatus();
            }
        },
        onClose: function () {
            _explorerEditorFile = null;
            _explorerEditorBaseDir = '';
        },
    });
}

// 현재 편집 중인 파일 경로 (어댑터 전용)
var _explorerEditorFile = null;
var _explorerEditorBaseDir = '';

/**
 * 편집기 열기 (app.js에서 호출)
 */
async function openEditor() {
    var currentPage = AppState.currentPage;
    if (!currentPage) {
        showToast('No document loaded', 'error');
        return;
    }

    // Plan-72 P3: 저작 .md 편집은 Author 셸 전용(MdEditor). Explorer 는 워드→HTML 소비만 담당하며
    // 저작 문서를 트리·딥링크로 노출하지 않으므로 여기의 .md 분기(구 Plan-60)는 제거됨.

    // 인증 필요 시 체크
    if (EDITOR_CONFIG.requireAuth && typeof requireAdmin === 'function') {
        requireAdmin(function () { _openEditorInner(); });
        return;
    }
    _openEditorInner();
}

async function _openEditorInner() {
    var currentPage = AppState.currentPage;
    if (!currentPage) {
        showToast('No document loaded', 'error');
        return;
    }

    _explorerEditorFile = currentPage;
    var idx = currentPage.lastIndexOf('/');
    _explorerEditorBaseDir = (idx >= 0) ? currentPage.substring(0, idx + 1) : '';

    try {
        var response = await fetch(currentPage + '?t=' + Date.now());
        if (!response.ok) throw new Error('Failed to load document');
        var content = await response.text();

        _explorerEditor.open(content, currentPage);
    } catch (error) {
        console.error('Error loading document:', error);
        showToast('Failed to load document', 'error');
    }
}

/**
 * 편집기 닫기
 */
function closeEditor(force) {
    if (_explorerEditor) {
        if (force) {
            _explorerEditor.close();
        } else {
            _explorerEditor.closeWithConfirm();
        }
    }
}

function closeEditorWithConfirm() {
    if (_explorerEditor) _explorerEditor.closeWithConfirm();
}

/**
 * 편집 버튼 표시/숨김 (app.js에서 호출)
 */
function updateEditButtonVisibility() {
    var navEditItem = document.getElementById('nav-edit-item');
    if (!navEditItem) return;

    if (!EDITOR_CONFIG.enabled) {
        navEditItem.style.display = 'none';
        return;
    }

    var currentPage = AppState.currentPage;
    var nonEditablePages = ['home.html', 'about.html'];
    var isEditable = currentPage &&
        !nonEditablePages.some(function (page) { return currentPage.includes(page); });

    navEditItem.style.display = isEditable ? '' : 'none';
}

// 하위 호환: EditorState 읽기 전용 프록시
var EditorState = {
    get isOpen() { return _explorerEditor ? _explorerEditor.isOpen() : false; },
    get isModified() { return _explorerEditor ? _explorerEditor.isModified() : false; },
    get editor() { return _explorerEditor ? _explorerEditor.getMonaco() : null; },
    get currentFile() { return _explorerEditorFile; },
};

// DOM 로드 시 편집기 초기화
document.addEventListener('DOMContentLoaded', function () {
    initEditor();
});
