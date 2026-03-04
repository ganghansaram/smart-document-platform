/* ===================================
   KF-21 웹북 - 메인 앱 로직
   =================================== */

// 전역 상태 관리
const AppState = {
    currentPage: null,
    menuData: null,
    searchIndex: null
};

// DOM이 로드되면 초기화
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

/**
 * 앱 초기화
 */
async function initializeApp() {
    // 표시 설정 적용 (body에 설정하여 팝업 등 전역 적용)
    applyDisplayConfig();

    // 다크/라이트 테마 초기화
    initTheme();

    // 북마크 기능 초기화
    if (typeof initBookmarks === 'function') {
        initBookmarks();
    }

    // 패널 토글 기능 초기화
    initPanelToggles();

    // 패널 리사이즈 기능 초기화
    initPanelResize();

    // 트리 메뉴 초기화
    initTreeMenu();

    // 펼치기/접기 버튼 초기화
    initExpandCollapseButtons();

    // 검색 기능 초기화
    initSearch();

    // 텍스트 선택 용어 조회 초기화
    if (typeof initGlossaryLookup === 'function') {
        initGlossaryLookup();
    }

    // 런타임 설정 로드 (settings.json → CONFIG 객체 오버라이드)
    await loadRuntimeSettings();

    // 런타임 설정이 siteTitle을 오버라이드했을 수 있으므로 재적용
    applyDisplayConfig();

    // 인증 초기화 (완료 후 Analytics 시작해야 username이 heartbeat에 포함됨)
    if (typeof initAuth === 'function') {
        await initAuth();
    }

    // Analytics 초기화
    if (typeof initAnalytics === 'function') {
        initAnalytics();
    }

    // URL 파라미터 페이지 또는 기본 홈 로드
    loadPageFromUrl() || loadContent('contents/home.html');
}

/**
 * 다크/라이트 테마 초기화 — localStorage 우선, 없으면 OS 설정 따름
 */
function initTheme() {
    var saved = localStorage.getItem('theme');
    if (saved === 'dark') {
        document.body.dataset.theme = 'dark';
    }

    var btn = document.getElementById('theme-toggle');
    if (btn) {
        btn.addEventListener('click', function() {
            var isDark = document.body.dataset.theme === 'dark';
            document.body.dataset.theme = isDark ? '' : 'dark';
            localStorage.setItem('theme', isDark ? 'light' : 'dark');
        });
    }
}

/**
 * 펼치기/접기 버튼 초기화
 */
function initExpandCollapseButtons() {
    // 좌측 트리 메뉴
    var expandLeft = document.getElementById('expand-all-left');
    var collapseLeft = document.getElementById('collapse-all-left');

    if (expandLeft) {
        expandLeft.addEventListener('click', function() {
            if (typeof expandAllTree === 'function') expandAllTree();
        });
    }
    if (collapseLeft) {
        collapseLeft.addEventListener('click', function() {
            if (typeof collapseAllTree === 'function') collapseAllTree();
        });
    }

    // 우측 섹션 네비게이터
    var expandRight = document.getElementById('expand-all-right');
    var collapseRight = document.getElementById('collapse-all-right');
    var toggleAutoTrackBtn = document.getElementById('toggle-auto-track');

    if (expandRight) {
        expandRight.addEventListener('click', function() {
            if (typeof expandAllSections === 'function') expandAllSections();
        });
    }
    if (collapseRight) {
        collapseRight.addEventListener('click', function() {
            if (typeof collapseAllSections === 'function') collapseAllSections();
        });
    }
    if (toggleAutoTrackBtn) {
        toggleAutoTrackBtn.addEventListener('click', function() {
            if (typeof toggleAutoTrack === 'function') toggleAutoTrack();
        });
    }
}

/**
 * 패널 토글 기능 초기화
 */
function initPanelToggles() {
    const leftPanel = document.getElementById('left-panel');
    const rightPanel = document.getElementById('right-panel');
    const toggleLeft = document.getElementById('toggle-left');
    const toggleRight = document.getElementById('toggle-right');
    const showLeft = document.getElementById('show-left');
    const showRight = document.getElementById('show-right');
    const container = document.querySelector('.container');

    // 좌측 패널 토글
    if (toggleLeft) {
        toggleLeft.addEventListener('click', function() {
            leftPanel.classList.add('hidden');
            showLeft.style.display = 'block';
            updateGridLayout();
        });
    }

    if (showLeft) {
        showLeft.addEventListener('click', function() {
            leftPanel.classList.remove('hidden');
            showLeft.style.display = 'none';
            updateGridLayout();
        });
    }

    // 우측 패널 토글
    if (toggleRight) {
        toggleRight.addEventListener('click', function() {
            rightPanel.classList.add('hidden');
            showRight.style.display = 'block';
            updateGridLayout();
        });
    }

    if (showRight) {
        showRight.addEventListener('click', function() {
            rightPanel.classList.remove('hidden');
            showRight.style.display = 'none';
            updateGridLayout();
        });
    }

    function updateGridLayout() {
        const leftHidden = leftPanel.classList.contains('hidden');
        const rightHidden = rightPanel.classList.contains('hidden');
        const leftWidth = leftPanel.dataset.width || '280px';
        const rightWidth = rightPanel.dataset.width || '240px';

        if (leftHidden && rightHidden) {
            container.style.gridTemplateColumns = '0 0 1fr 0 0';
        } else if (leftHidden) {
            container.style.gridTemplateColumns = `0 0 1fr 4px ${rightWidth}`;
        } else if (rightHidden) {
            container.style.gridTemplateColumns = `${leftWidth} 4px 1fr 0 0`;
        } else {
            container.style.gridTemplateColumns = `${leftWidth} 4px 1fr 4px ${rightWidth}`;
        }

    }
}

/**
 * 패널 리사이즈 기능 초기화
 */
function initPanelResize() {
    const container = document.querySelector('.container');
    const leftPanel = document.getElementById('left-panel');
    const rightPanel = document.getElementById('right-panel');
    const resizeLeft = document.getElementById('resize-left');
    const resizeRight = document.getElementById('resize-right');

    // 최소/최대 너비 설정
    const MIN_WIDTH = 180;
    const MAX_WIDTH = 450;

    let isResizing = false;
    let currentHandle = null;

    // 좌측 핸들 드래그
    if (resizeLeft) {
        resizeLeft.addEventListener('mousedown', (e) => {
            if (leftPanel.classList.contains('hidden')) return;
            isResizing = true;
            currentHandle = 'left';
            resizeLeft.classList.add('dragging');
            document.body.classList.add('resizing');
            e.preventDefault();
        });
    }

    // 우측 핸들 드래그
    if (resizeRight) {
        resizeRight.addEventListener('mousedown', (e) => {
            if (rightPanel.classList.contains('hidden')) return;
            isResizing = true;
            currentHandle = 'right';
            resizeRight.classList.add('dragging');
            document.body.classList.add('resizing');
            e.preventDefault();
        });
    }

    // 마우스 이동
    document.addEventListener('mousemove', (e) => {
        if (!isResizing) return;

        const containerRect = container.getBoundingClientRect();

        if (currentHandle === 'left') {
            let newWidth = e.clientX - containerRect.left;
            newWidth = Math.max(MIN_WIDTH, Math.min(MAX_WIDTH, newWidth));
            leftPanel.dataset.width = newWidth + 'px';
            updateLayout();
        } else if (currentHandle === 'right') {
            let newWidth = containerRect.right - e.clientX;
            newWidth = Math.max(MIN_WIDTH, Math.min(MAX_WIDTH, newWidth));
            rightPanel.dataset.width = newWidth + 'px';
            updateLayout();
        }
    });

    // 마우스 업
    document.addEventListener('mouseup', () => {
        if (isResizing) {
            isResizing = false;
            currentHandle = null;
            resizeLeft?.classList.remove('dragging');
            resizeRight?.classList.remove('dragging');
            document.body.classList.remove('resizing');
        }
    });

    function updateLayout() {
        const leftHidden = leftPanel.classList.contains('hidden');
        const rightHidden = rightPanel.classList.contains('hidden');
        const leftWidth = leftPanel.dataset.width || '280px';
        const rightWidth = rightPanel.dataset.width || '240px';

        if (leftHidden && rightHidden) {
            container.style.gridTemplateColumns = '0 0 1fr 0 0';
        } else if (leftHidden) {
            container.style.gridTemplateColumns = `0 0 1fr 4px ${rightWidth}`;
        } else if (rightHidden) {
            container.style.gridTemplateColumns = `${leftWidth} 4px 1fr 0 0`;
        } else {
            container.style.gridTemplateColumns = `${leftWidth} 4px 1fr 4px ${rightWidth}`;
        }
    }
}

/**
 * DISPLAY_CONFIG → DOM 반영 (초기화 + 런타임 설정 후 재호출)
 */
function applyDisplayConfig() {
    if (typeof DISPLAY_CONFIG === 'undefined') return;

    if (DISPLAY_CONFIG.siteTitle) {
        var logoH1 = document.querySelector('.logo h1');
        if (logoH1) logoH1.textContent = DISPLAY_CONFIG.siteTitle;
        document.title = DISPLAY_CONFIG.siteTitle;
    }
    if (DISPLAY_CONFIG.tableStyle) {
        document.body.dataset.tableStyle = DISPLAY_CONFIG.tableStyle;
    }
    if (DISPLAY_CONFIG.version) {
        var versionEl = document.querySelector('.footer-version');
        if (versionEl) versionEl.textContent = DISPLAY_CONFIG.version;
    }
    if (DISPLAY_CONFIG.platformName) {
        var platformEl = document.querySelector('.footer-platform');
        if (platformEl) platformEl.textContent = DISPLAY_CONFIG.platformName;
    }
}

/**
 * 콘텐츠 로드
 */
function loadContent(url) {
    const mainContent = document.getElementById('main-content');
    const contentPanel = document.getElementById('content-panel');

    if (!url) {
        mainContent.innerHTML = '<h1>페이지를 찾을 수 없습니다</h1><p>요청하신 페이지가 존재하지 않습니다.</p>';
        return;
    }

    // 용어집 페이지: 데이터 기반 동적 렌더링
    if (url === 'glossary:terms') {
        if (typeof pauseSlideshow === 'function') pauseSlideshow();
        AppState.currentPage = url;
        updatePageUrl(url);
        if (typeof highlightCurrentPage === 'function') highlightCurrentPage(url);
        if (typeof renderGlossaryPage === 'function') renderGlossaryPage();
        updateBreadcrumb(url);
        return;
    }

    // 대시보드 페이지: API 기반 동적 렌더링
    if (url === 'analytics:dashboard') {
        if (typeof pauseSlideshow === 'function') pauseSlideshow();
        AppState.currentPage = url;
        updatePageUrl(url);
        if (typeof highlightCurrentPage === 'function') highlightCurrentPage(url);
        if (typeof renderAnalyticsDashboard === 'function') renderAnalyticsDashboard();
        updateBreadcrumb(url);
        return;
    }

    // 페이지 이동 시 슬라이드쇼 정리 (홈이 아닌 경우에도 interval 정리)
    if (typeof pauseSlideshow === 'function') {
        pauseSlideshow();
    }

    // 로딩 오버레이 표시
    showLoadingOverlay(contentPanel);

    // 콘텐츠 파일의 디렉토리 경로 추출 (상대 경로 변환용)
    const baseDir = url.substring(0, url.lastIndexOf('/') + 1);

    // 콘텐츠 로드 (캐시 버스팅)
    fetch(url + '?t=' + Date.now())
        .then(response => {
            if (!response.ok) {
                throw new Error('페이지를 불러올 수 없습니다.');
            }
            return response.text();
        })
        .then(html => {
            // 상대 경로를 콘텐츠 파일 기준 절대 경로로 변환
            html = resolveRelativePaths(html, baseDir);
            // 이미지 비동기 디코딩 + 섹션 래핑 적용
            html = optimizeContent(html);
            mainContent.innerHTML = html;
            AppState.currentPage = url;

            // Analytics: page view tracking
            if (typeof trackPageView === 'function') {
                trackPageView(url);
            }

            // 무거운 작업을 다음 프레임으로 미뤄 로딩 UI가 보이도록 함
            requestAnimationFrame(function() {
                // 섹션 네비게이터 업데이트 (목차 생성 + 위치 캐싱)
                if (typeof updateSectionNav === 'function') {
                    updateSectionNav();
                }

                // 헤딩에 북마크 아이콘 주입 (섹션 네비게이터가 ID 부여한 뒤)
                if (typeof injectBookmarkIcons === 'function') {
                    injectBookmarkIcons();
                }

                // 트리 메뉴에서 현재 페이지 하이라이트
                if (typeof highlightCurrentPage === 'function') {
                    highlightCurrentPage(url);
                }

                // 브레드크럼 업데이트
                updateBreadcrumb(url);

                // 홈 페이지인 경우 배너 슬라이드쇼 및 섹션 링크 초기화
                if (url.includes('home.html')) {
                    if (typeof initBannerSlideshow === 'function') {
                        initBannerSlideshow();
                    }
                    if (typeof generateSectionLinks === 'function') {
                        generateSectionLinks();
                    }
                }

                // 스크롤 처리: 대기 중인 섹션이 있으면 해당 섹션으로, 없으면 상단으로
                if (window._pendingScrollToSection) {
                    var targetEl = document.getElementById(window._pendingScrollToSection);
                    // 분할 섹션 ID(-2, -3 등)가 없으면 원본 ID로 폴백
                    if (!targetEl) {
                        var baseId = window._pendingScrollToSection.replace(/-\d+$/, '');
                        targetEl = document.getElementById(baseId);
                    }
                    if (targetEl) {
                        scrollToElementReliably(targetEl);
                    }
                    window._pendingScrollToSection = null;
                } else {
                    contentPanel.scrollTop = 0;
                }

                // 검색어 하이라이트 처리
                if (window._pendingHighlightQuery) {
                    if (typeof highlightSearchTermsInContent === 'function') {
                        highlightSearchTermsInContent(window._pendingHighlightQuery);
                    }
                    window._pendingHighlightQuery = null;
                }

                // 편집 버튼 표시 업데이트
                if (typeof updateEditButtonVisibility === 'function') {
                    updateEditButtonVisibility();
                }

                // 본문 약어 하이라이트 (용어집 점선 밑줄)
                if (typeof highlightGlossaryTermsInContent === 'function') {
                    highlightGlossaryTermsInContent();
                }

                // 로딩 완료 후 오버레이 숨김
                hideLoadingOverlay(contentPanel);
            });
        })
        .catch(error => {
            console.error('콘텐츠 로드 오류:', error);
            mainContent.innerHTML = `
                <h1>오류가 발생했습니다</h1>
                <p>${error.message}</p>
                <p>파일 경로: <code>${url}</code></p>
            `;
            hideLoadingOverlay(contentPanel);
        });
}

/**
 * 로딩 오버레이 표시
 */
function showLoadingOverlay(container) {
    // 기존 오버레이 제거
    hideLoadingOverlay(container);

    var overlay = document.createElement('div');
    overlay.className = 'loading-overlay';
    overlay.innerHTML = '<div class="loading-spinner"></div><span class="loading-text">Loading...</span>';
    container.style.position = 'relative';
    container.appendChild(overlay);
}

/**
 * 로딩 오버레이 숨김
 */
function hideLoadingOverlay(container) {
    var overlay = container.querySelector('.loading-overlay');
    if (overlay) {
        overlay.remove();
    }
}

/**
 * URL 파라미터에서 페이지 로드 (북마크/공유 지원)
 */
function loadPageFromUrl() {
    const urlParams = new URLSearchParams(window.location.search);
    const page = urlParams.get('page');

    if (page) {
        loadContent(page);
        return true;
    }
    return false;
}

/**
 * 페이지 URL 업데이트 (북마크/공유 가능하게)
 */
function updatePageUrl(pageUrl) {
    const newUrl = `${window.location.pathname}?page=${encodeURIComponent(pageUrl)}`;
    window.history.pushState({ page: pageUrl }, '', newUrl);
}

/**
 * 콘텐츠 HTML 내 상대 경로를 콘텐츠 파일 기준으로 변환
 */
function resolveRelativePaths(html, baseDir) {
    if (!baseDir) return html;

    var doc = new DOMParser().parseFromString(html, 'text/html');

    // 변환 대상: img src, source src, video/audio poster
    var attrMap = [
        { selector: 'img[src]', attr: 'src' },
        { selector: 'source[src]', attr: 'src' },
        { selector: '[poster]', attr: 'poster' }
    ];

    attrMap.forEach(function(entry) {
        doc.querySelectorAll(entry.selector).forEach(function(el) {
            var val = el.getAttribute(entry.attr);
            if (val && !val.startsWith('/') && !val.startsWith('http://') &&
                !val.startsWith('https://') && !val.startsWith('data:') &&
                !val.startsWith('#')) {
                el.setAttribute(entry.attr, baseDir + val);
            }
        });
    });

    return doc.body.innerHTML;
}

/**
 * content-visibility:auto 호환 스크롤 (반복 수렴 방식)
 * instant 스크롤 → 주변 섹션 렌더링 → 위치 재확인 → 수렴할 때까지 반복
 * content-visibility를 건드리지 않으므로 퍼포먼스 이점 유지
 */
function scrollToElementReliably(el) {
    if (!el) return;

    var maxAttempts = 10;
    var attempts = 0;
    var contentPanel = document.getElementById('content-panel');
    if (!contentPanel) return;

    function tryScroll() {
        var panelRect = contentPanel.getBoundingClientRect();
        var elRect = el.getBoundingClientRect();
        var offset = elRect.top - panelRect.top;

        // 목표 위치에 도달했으면 종료 (scroll-margin-top 20px 고려, 허용 오차 5px)
        if (Math.abs(offset - 20) < 5 || attempts >= maxAttempts) {
            return;
        }

        attempts++;
        el.scrollIntoView({ block: 'start' });

        // 다음 프레임에서 재확인 (스크롤로 새 섹션이 렌더링되면 위치가 변할 수 있음)
        requestAnimationFrame(tryScroll);
    }

    tryScroll();
}

/**
 * 콘텐츠 최적화: 이미지 비동기 디코딩 + 섹션 단위 래핑
 * - decoding="async": 이미지 전부 즉시 로드하되 디코딩만 비동기 처리
 * - 섹션 래핑: h1/h2 기준으로 content-section div로 감싸 content-visibility 적용
 */
function optimizeContent(html) {
    var doc = new DOMParser().parseFromString(html, 'text/html');

    // 1단계: 이미지 비동기 디코딩
    doc.querySelectorAll('img').forEach(function(img) {
        if (!img.hasAttribute('decoding')) {
            img.setAttribute('decoding', 'async');
        }
    });

    // 2단계: 캡션 자동 감지 - Figure/Table/그림/표 패턴의 짧은 <p>에 class="caption" 부여
    var captionPattern = /^(Figure|Table|그림|표|Fig\.)\s*\d/i;
    doc.querySelectorAll('p').forEach(function(p) {
        if (p.classList.contains('caption')) return;
        var text = p.textContent.trim();
        if (captionPattern.test(text) && text.length < 150) {
            p.classList.add('caption');
        }
    });

    // 3단계: h1/h2 기준 섹션 래핑
    var body = doc.body;
    var children = Array.from(body.childNodes);
    var fragment = document.createDocumentFragment();
    var currentSection = null;

    children.forEach(function(node) {
        var tagName = node.tagName ? node.tagName.toUpperCase() : '';

        if (tagName === 'H1' || tagName === 'H2') {
            // 이전 섹션이 있으면 fragment에 추가
            if (currentSection) {
                fragment.appendChild(currentSection);
            }
            // 새 섹션 시작
            currentSection = document.createElement('div');
            currentSection.className = 'content-section';
            currentSection.appendChild(node);
        } else if (currentSection) {
            currentSection.appendChild(node);
        } else {
            // 첫 h1/h2 이전의 콘텐츠는 그대로 유지
            fragment.appendChild(node);
        }
    });

    // 마지막 섹션 추가
    if (currentSection) {
        fragment.appendChild(currentSection);
    }

    body.innerHTML = '';
    body.appendChild(fragment);

    return body.innerHTML;
}

/**
 * 공용 토스트 알림 표시
 * @param {string} message - 표시할 메시지
 * @param {string} [type] - 'success' | 'error' | 'warning' (기본: info)
 */
function showToast(message, type) {
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
    toast._timer = setTimeout(function() {
        toast.classList.remove('show');
    }, 3000);
}

// 브라우저 뒤로가기/앞으로가기 지원
window.addEventListener('popstate', function(event) {
    if (event.state && event.state.page) {
        loadContent(event.state.page);
    } else {
        // 초기 상태(홈)로 돌아온 경우
        loadContent('contents/home.html');
    }
});

/* ===================================
   브레드크럼 내비게이션
   =================================== */

/**
 * 메뉴 데이터에서 URL 경로 찾기 (재귀)
 */
function findMenuPath(items, targetUrl, path) {
    for (var i = 0; i < items.length; i++) {
        var item = items[i];
        var currentPath = path.concat([{ label: item.label, url: item.url || null }]);

        if (item.url === targetUrl) {
            return currentPath;
        }
        if (item.children) {
            var found = findMenuPath(item.children, targetUrl, currentPath);
            if (found) return found;
        }
    }
    return null;
}

/**
 * 브레드크럼 업데이트
 */
function updateBreadcrumb(url) {
    var mainContent = document.getElementById('main-content');
    if (!mainContent) return;

    // 기존 브레드크럼 제거
    var existing = mainContent.querySelector('.breadcrumb');
    if (existing) existing.remove();

    // 홈 페이지에서는 브레드크럼 숨김
    if (!url || url.includes('home.html')) return;

    function renderBreadcrumb(menuData) {
        var pathItems = findMenuPath(menuData, url, []);
        if (!pathItems || pathItems.length <= 1) return;

        var nav = document.createElement('nav');
        nav.className = 'breadcrumb';

        // 홈 링크
        var homeLink = document.createElement('a');
        homeLink.href = '#';
        homeLink.textContent = '홈';
        homeLink.addEventListener('click', function(e) {
            e.preventDefault();
            loadContent('contents/home.html');
        });
        var homeItem = document.createElement('span');
        homeItem.className = 'breadcrumb-item';
        homeItem.appendChild(homeLink);
        nav.appendChild(homeItem);

        // 경로 항목
        for (var i = 0; i < pathItems.length; i++) {
            // 구분자
            var sep = document.createElement('span');
            sep.className = 'breadcrumb-separator';
            sep.textContent = '›';
            nav.appendChild(sep);

            var crumb = document.createElement('span');
            crumb.className = 'breadcrumb-item';

            if (i < pathItems.length - 1 && pathItems[i].url) {
                var link = document.createElement('a');
                link.href = '#';
                link.textContent = pathItems[i].label.replace(/\s*\(.*$/, '');
                (function(navUrl) {
                    link.addEventListener('click', function(e) {
                        e.preventDefault();
                        loadContent(navUrl);
                    });
                })(pathItems[i].url);
                crumb.appendChild(link);
            } else if (i === pathItems.length - 1) {
                var current = document.createElement('span');
                current.className = 'breadcrumb-current';
                current.textContent = pathItems[i].label;
                current.title = pathItems[i].label;
                crumb.appendChild(current);
            } else {
                var text = document.createElement('span');
                text.textContent = pathItems[i].label.replace(/\s*\(.*$/, '');
                crumb.appendChild(text);
            }

            nav.appendChild(crumb);
        }

        // main-content 첫 번째 자식으로 삽입
        mainContent.insertBefore(nav, mainContent.firstChild);
    }

    // 캐시된 메뉴 데이터 사용
    if (AppState.menuData) {
        renderBreadcrumb(AppState.menuData);
    } else {
        fetch('data/menu.json?t=' + Date.now())
            .then(function(r) { return r.json(); })
            .then(function(data) { renderBreadcrumb(data); })
            .catch(function() { /* skip */ });
    }
}

/* ===================================
   런타임 설정 로드 (settings.json → CONFIG 오버라이드)
   =================================== */

async function loadRuntimeSettings() {
    try {
        var backendUrl = (typeof AUTH_CONFIG !== 'undefined') ? AUTH_CONFIG.backendUrl : 'http://localhost:8000';
        var r = await fetch(backendUrl + '/api/settings/public');
        if (!r.ok) return;
        var data = await r.json();
        var f = data.frontend || {};

        if (typeof AI_CONFIG !== 'undefined') {
            if (f.ai_enabled          !== undefined) AI_CONFIG.enabled          = f.ai_enabled;
            if (f.ai_use_backend      !== undefined) AI_CONFIG.useBackend        = f.ai_use_backend;
            if (f.ai_search_type      !== undefined) AI_CONFIG.searchType        = f.ai_search_type;
            if (f.ai_max_search_results !== undefined) AI_CONFIG.maxSearchResults = f.ai_max_search_results;
            if (f.ai_max_context_length !== undefined) AI_CONFIG.maxContextLength = f.ai_max_context_length;
            if (f.ai_system_prompt    !== undefined) AI_CONFIG.systemPrompt      = f.ai_system_prompt;
        }
        if (typeof EDITOR_CONFIG !== 'undefined') {
            if (f.editor_enabled           !== undefined) EDITOR_CONFIG.enabled          = f.editor_enabled;
            if (f.editor_auto_save_interval !== undefined) EDITOR_CONFIG.autoSaveInterval = f.editor_auto_save_interval;
            if (f.editor_create_backup     !== undefined) EDITOR_CONFIG.createBackup     = f.editor_create_backup;
        }
        if (typeof UPLOAD_CONFIG !== 'undefined') {
            if (f.upload_enabled            !== undefined) UPLOAD_CONFIG.enabled          = f.upload_enabled;
            if (f.upload_auto_search_index  !== undefined) UPLOAD_CONFIG.autoSearchIndex  = f.upload_auto_search_index;
            if (f.upload_auto_vector_index  !== undefined) UPLOAD_CONFIG.autoVectorIndex  = f.upload_auto_vector_index;
            if (f.upload_max_file_size_mb   !== undefined) UPLOAD_CONFIG.maxFileSize      = f.upload_max_file_size_mb * 1024 * 1024;
        }
        if (typeof DISPLAY_CONFIG !== 'undefined') {
            if (f.display_table_style !== undefined) DISPLAY_CONFIG.tableStyle = f.display_table_style;
            if (f.display_site_title  !== undefined) DISPLAY_CONFIG.siteTitle  = f.display_site_title;
        }
        if (typeof AUTH_CONFIG !== 'undefined') {
            if (f.login_required !== undefined) AUTH_CONFIG.loginRequired = f.login_required;
        }
    } catch (e) {
        // 백엔드 미연결 시 config.js 기본값 유지
    }
}
