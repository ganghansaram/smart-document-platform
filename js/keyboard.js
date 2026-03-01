/* ===================================
   KF-21 웹북 - 키보드 단축키
   =================================== */

(function() {
    'use strict';

    var shortcutsOverlay = null;

    var SHORTCUTS = [
        { key: '?', description: '단축키 도움말' },
        { key: '/', description: '검색 열기' },
        { key: 'Ctrl+K', description: '검색 열기' },
        { key: 'Esc', description: '모달/오버레이 닫기' },
        { key: '\u2190', description: '이전 문서로 이동' },
        { key: '\u2192', description: '다음 문서로 이동' },
        { key: 'H', description: '홈으로 이동' },
        { key: 'B', description: '북마크 열기' }
    ];

    document.addEventListener('DOMContentLoaded', initKeyboardShortcuts);

    function initKeyboardShortcuts() {
        document.addEventListener('keydown', handleKeyboardShortcut);
    }

    /**
     * 키 분기 처리
     */
    function handleKeyboardShortcut(e) {
        // 입력 필드 활성 시 단축키 무시
        var tag = e.target.tagName;
        if (tag === 'INPUT' || tag === 'TEXTAREA' || e.target.isContentEditable) {
            return;
        }

        // 단축키 모달이 열려있으면 ? 또는 Esc로만 닫기
        if (shortcutsOverlay && shortcutsOverlay.classList.contains('active')) {
            if (e.key === 'Escape' || e.key === '?') {
                e.preventDefault();
                closeShortcutsHelp();
            }
            return;
        }

        // 다른 오버레이가 열려있으면 단축키 무시 (Esc는 각 모듈이 처리)
        if (isOverlayOpen()) {
            return;
        }

        // Ctrl+K → 검색
        if (e.key === 'k' && (e.ctrlKey || e.metaKey)) {
            e.preventDefault();
            if (typeof openSearchOverlay === 'function') {
                openSearchOverlay();
            }
            return;
        }

        // modifier 키 조합은 여기서 무시 (Ctrl+K 제외, 이미 처리됨)
        if (e.ctrlKey || e.metaKey || e.altKey) {
            return;
        }

        switch (e.key) {
            case '?':
                e.preventDefault();
                toggleShortcutsHelp();
                break;
            case '/':
                e.preventDefault();
                if (typeof openSearchOverlay === 'function') {
                    openSearchOverlay();
                }
                break;
            case 'ArrowLeft':
                e.preventDefault();
                navigateDocument(-1);
                break;
            case 'ArrowRight':
                e.preventDefault();
                navigateDocument(1);
                break;
            case 'h':
            case 'H':
                e.preventDefault();
                if (typeof loadContent === 'function') {
                    loadContent('contents/home.html');
                }
                break;
            case 'b':
            case 'B':
                e.preventDefault();
                if (typeof openBookmarksOverlay === 'function') {
                    openBookmarksOverlay();
                }
                break;
        }
    }

    /**
     * 오버레이(검색/북마크/팝업 등)가 열려있는지 확인
     */
    function isOverlayOpen() {
        var ids = ['search-overlay', 'bookmarks-overlay', 'figure-popup-overlay'];
        for (var i = 0; i < ids.length; i++) {
            var el = document.getElementById(ids[i]);
            if (el && el.classList.contains('active')) {
                return true;
            }
        }
        return false;
    }

    /**
     * 이전/다음 문서 이동
     */
    function navigateDocument(direction) {
        if (typeof AppState === 'undefined' || !AppState.menuData || !AppState.currentPage) {
            return;
        }
        var flat = flattenMenu(AppState.menuData);
        if (flat.length === 0) return;

        var currentIdx = -1;
        for (var i = 0; i < flat.length; i++) {
            if (flat[i].url === AppState.currentPage) {
                currentIdx = i;
                break;
            }
        }
        if (currentIdx === -1) return;

        var nextIdx = currentIdx + direction;
        if (nextIdx < 0) { showToast('첫 번째 문서입니다'); return; }
        if (nextIdx >= flat.length) { showToast('마지막 문서입니다'); return; }

        if (typeof loadContent === 'function') {
            loadContent(flat[nextIdx].url);
        }
    }

    /**
     * 메뉴 트리를 url 있는 항목만 순차 배열로 평탄화
     */
    function flattenMenu(items) {
        var result = [];
        for (var i = 0; i < items.length; i++) {
            var item = items[i];
            if (item.url) {
                result.push(item);
            }
            if (item.children && item.children.length > 0) {
                var children = flattenMenu(item.children);
                for (var j = 0; j < children.length; j++) {
                    result.push(children[j]);
                }
            }
        }
        return result;
    }

    // --- 도움말 모달 ---

    function toggleShortcutsHelp() {
        if (shortcutsOverlay && shortcutsOverlay.classList.contains('active')) {
            closeShortcutsHelp();
        } else {
            showShortcutsHelp();
        }
    }

    function showShortcutsHelp() {
        if (!shortcutsOverlay) {
            shortcutsOverlay = createShortcutsModal();
            document.body.appendChild(shortcutsOverlay);
        }
        // Force reflow before adding active class for transition
        shortcutsOverlay.offsetHeight;
        shortcutsOverlay.classList.add('active');
    }

    function closeShortcutsHelp() {
        if (shortcutsOverlay) {
            shortcutsOverlay.classList.remove('active');
        }
    }

    /**
     * 도움말 모달 DOM 동적 생성
     */
    function createShortcutsModal() {
        var overlay = document.createElement('div');
        overlay.id = 'shortcuts-overlay';
        overlay.className = 'shortcuts-overlay';

        var modal = document.createElement('div');
        modal.className = 'shortcuts-modal';

        // 헤더
        var header = document.createElement('div');
        header.className = 'shortcuts-header';

        var title = document.createElement('h2');
        title.textContent = '\ud0a4\ubcf4\ub4dc \ub2e8\ucd95\ud0a4';

        var closeBtn = document.createElement('button');
        closeBtn.className = 'shortcuts-close';
        closeBtn.innerHTML = '&times;';
        closeBtn.addEventListener('click', closeShortcutsHelp);

        header.appendChild(title);
        header.appendChild(closeBtn);

        // 본문
        var body = document.createElement('div');
        body.className = 'shortcuts-body';

        var group = document.createElement('div');
        group.className = 'shortcuts-group';

        for (var i = 0; i < SHORTCUTS.length; i++) {
            var row = document.createElement('div');
            row.className = 'shortcut-row';

            var kbd = document.createElement('kbd');
            kbd.textContent = SHORTCUTS[i].key;

            var desc = document.createElement('span');
            desc.textContent = SHORTCUTS[i].description;

            row.appendChild(kbd);
            row.appendChild(desc);
            group.appendChild(row);
        }

        body.appendChild(group);

        modal.appendChild(header);
        modal.appendChild(body);
        overlay.appendChild(modal);

        // 배경 클릭 시 닫기
        overlay.addEventListener('click', function(e) {
            if (e.target === overlay) {
                closeShortcutsHelp();
            }
        });

        return overlay;
    }
})();
