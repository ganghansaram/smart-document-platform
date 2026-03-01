/* ===================================
   KF-21 웹북 - 북마크 기능
   =================================== */

var BOOKMARKS_STORAGE_KEY = 'webbook-bookmarks';

/**
 * 북마크 초기화 — 오버레이 이벤트 바인딩
 */
function initBookmarks() {
    var trigger = document.getElementById('bookmarks-trigger');
    var closeBtn = document.getElementById('bookmarks-close');
    var overlay = document.getElementById('bookmarks-overlay');

    if (trigger) {
        trigger.addEventListener('click', function(e) {
            e.preventDefault();
            openBookmarksOverlay();
        });
    }

    if (closeBtn) {
        closeBtn.addEventListener('click', closeBookmarksOverlay);
    }

    // 전체 삭제 버튼
    var clearAllBtn = document.getElementById('bookmarks-clear-all');
    if (clearAllBtn) {
        clearAllBtn.addEventListener('click', function() {
            if (confirm('모든 북마크를 삭제하시겠습니까?')) {
                saveBookmarks([]);
                renderBookmarksList();
                refreshBookmarkIcons();
            }
        });
    }

    // 오버레이 배경 클릭으로 닫기
    if (overlay) {
        overlay.addEventListener('click', function(e) {
            if (e.target === overlay) {
                closeBookmarksOverlay();
            }
        });
    }

    // ESC 키로 닫기
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && overlay && overlay.classList.contains('active')) {
            closeBookmarksOverlay();
        }
    });
}

/**
 * localStorage에서 북마크 읽기
 */
function loadBookmarks() {
    try {
        var data = localStorage.getItem(BOOKMARKS_STORAGE_KEY);
        return data ? JSON.parse(data) : [];
    } catch (e) {
        console.error('북마크 로드 오류:', e);
        return [];
    }
}

/**
 * localStorage에 북마크 저장
 */
function saveBookmarks(bookmarks) {
    try {
        localStorage.setItem(BOOKMARKS_STORAGE_KEY, JSON.stringify(bookmarks));
    } catch (e) {
        console.error('북마크 저장 오류:', e);
    }
}

/**
 * 북마크 오버레이 열기
 */
function openBookmarksOverlay() {
    var overlay = document.getElementById('bookmarks-overlay');
    if (overlay) {
        renderBookmarksList();
        overlay.classList.add('active');
    }
}

/**
 * 북마크 오버레이 닫기
 */
function closeBookmarksOverlay() {
    var overlay = document.getElementById('bookmarks-overlay');
    if (overlay) {
        overlay.classList.remove('active');
    }
}

/**
 * 오버레이 목록 렌더링 — 문서별 그룹핑
 */
function renderBookmarksList() {
    var listEl = document.getElementById('bookmarks-list');
    var emptyEl = document.querySelector('.bookmarks-empty');
    var clearAllBtn = document.getElementById('bookmarks-clear-all');
    if (!listEl) return;

    var bookmarks = loadBookmarks();

    if (bookmarks.length === 0) {
        listEl.style.display = 'none';
        if (emptyEl) emptyEl.style.display = 'block';
        if (clearAllBtn) clearAllBtn.style.display = 'none';
        return;
    }

    listEl.style.display = 'block';
    if (emptyEl) emptyEl.style.display = 'none';
    if (clearAllBtn) clearAllBtn.style.display = 'inline-block';

    // 문서별 그룹핑
    var groups = {};
    bookmarks.forEach(function(bm) {
        var key = bm.pagePath;
        if (!groups[key]) {
            groups[key] = { pageTitle: bm.pageTitle, items: [] };
        }
        groups[key].items.push(bm);
    });

    var html = '';
    Object.keys(groups).forEach(function(pagePath) {
        var group = groups[pagePath];
        html += '<div class="bookmarks-group">';
        html += '<div class="bookmarks-group-title">' + escapeHtml(group.pageTitle) + '</div>';
        group.items.forEach(function(bm) {
            html += '<div class="bookmarks-item" data-id="' + bm.id + '">';
            html += '<a href="#" class="bookmarks-item-link" data-page="' + escapeHtml(bm.pagePath) + '" data-section="' + escapeHtml(bm.sectionId) + '">';
            html += escapeHtml(bm.sectionTitle);
            html += '</a>';
            html += '<button class="bookmarks-item-delete" data-id="' + bm.id + '" title="삭제">&times;</button>';
            html += '</div>';
        });
        html += '</div>';
    });

    listEl.innerHTML = html;

    // 항목 클릭 이벤트
    listEl.querySelectorAll('.bookmarks-item-link').forEach(function(link) {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            var pagePath = this.getAttribute('data-page');
            var sectionId = this.getAttribute('data-section');
            closeBookmarksOverlay();
            navigateToBookmark(pagePath, sectionId);
        });
    });

    // 삭제 버튼 이벤트
    listEl.querySelectorAll('.bookmarks-item-delete').forEach(function(btn) {
        btn.addEventListener('click', function(e) {
            e.stopPropagation();
            var id = Number(this.getAttribute('data-id'));
            removeBookmarkById(id);
            renderBookmarksList();
            // 현재 문서의 아이콘 상태도 갱신
            refreshBookmarkIcons();
        });
    });
}

/**
 * ID로 북마크 제거
 */
function removeBookmarkById(id) {
    var bookmarks = loadBookmarks();
    bookmarks = bookmarks.filter(function(bm) { return bm.id !== id; });
    saveBookmarks(bookmarks);
}

/**
 * 해당 문서/섹션으로 이동
 */
function navigateToBookmark(pagePath, sectionId) {
    var contentPanel = document.getElementById('content-panel');

    // 같은 문서인 경우 스크롤만
    if (AppState.currentPage === pagePath) {
        var el = document.getElementById(sectionId);
        if (el) {
            scrollToElementReliably(el);
        }
    } else {
        // 다른 문서: 로드 후 스크롤
        window._pendingScrollToSection = sectionId;
        loadContent(pagePath);
    }
}

/**
 * 이미 북마크 되었는지 확인
 */
function isBookmarked(pagePath, sectionId) {
    var bookmarks = loadBookmarks();
    return bookmarks.some(function(bm) {
        return bm.pagePath === pagePath && bm.sectionId === sectionId;
    });
}

/**
 * 헤딩의 북마크 추가/제거 토글
 */
function toggleBookmark(headingEl) {
    var pagePath = AppState.currentPage;
    if (!pagePath) return;

    var sectionId = headingEl.id;
    if (!sectionId) return;

    var bookmarks = loadBookmarks();
    var existingIdx = -1;
    for (var i = 0; i < bookmarks.length; i++) {
        if (bookmarks[i].pagePath === pagePath && bookmarks[i].sectionId === sectionId) {
            existingIdx = i;
            break;
        }
    }

    if (existingIdx >= 0) {
        // 제거
        bookmarks.splice(existingIdx, 1);
    } else {
        // 추가
        var pageTitle = getPageTitle();
        bookmarks.push({
            id: Date.now(),
            pagePath: pagePath,
            pageTitle: pageTitle,
            sectionId: sectionId,
            sectionTitle: headingEl.textContent.replace(/[^\S\n]+$/g, '').trim(),
            timestamp: new Date().toISOString()
        });
    }

    saveBookmarks(bookmarks);

    // 아이콘 상태 갱신
    var icon = headingEl.querySelector('.bookmark-icon');
    if (icon) {
        icon.classList.toggle('active', existingIdx < 0);
    }

    showToast(existingIdx < 0 ? '북마크에 추가됨' : '북마크에서 제거됨');
}

/**
 * 현재 문서의 제목(h1) 추출
 */
function getPageTitle() {
    var mainContent = document.getElementById('main-content');
    if (!mainContent) return '';
    var h1 = mainContent.querySelector('h1');
    return h1 ? h1.textContent.trim() : (AppState.currentPage || '');
}

/**
 * 현재 문서의 h1~h4 헤딩에 북마크 아이콘 삽입
 */
function injectBookmarkIcons() {
    var mainContent = document.getElementById('main-content');
    if (!mainContent) return;

    var pagePath = AppState.currentPage;
    if (!pagePath) return;

    var headings = mainContent.querySelectorAll('h1[id], h2[id], h3[id], h4[id]');

    headings.forEach(function(heading) {
        // 이미 아이콘이 있으면 스킵
        if (heading.querySelector('.bookmark-icon')) return;

        var icon = document.createElement('span');
        icon.className = 'bookmark-icon';
        icon.title = '북마크';

        // 이미 북마크된 헤딩이면 활성화
        if (isBookmarked(pagePath, heading.id)) {
            icon.classList.add('active');
        }

        icon.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            toggleBookmark(heading);
        });

        heading.appendChild(icon);
    });
}

/**
 * 현재 문서의 북마크 아이콘 활성 상태 갱신
 */
function refreshBookmarkIcons() {
    var mainContent = document.getElementById('main-content');
    if (!mainContent) return;

    var pagePath = AppState.currentPage;
    if (!pagePath) return;

    mainContent.querySelectorAll('.bookmark-icon').forEach(function(icon) {
        var heading = icon.parentElement;
        if (heading && heading.id) {
            icon.classList.toggle('active', isBookmarked(pagePath, heading.id));
        }
    });
}

/**
 * HTML 이스케이프
 */
function escapeHtml(str) {
    var div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}
