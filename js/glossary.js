/* ===================================
   항공 용어집 (Aviation Glossary)
   =================================== */

// 모듈 상태
var _glossaryData = null;       // 전체 배열 (glossary.json)
var _glossaryIndex = {};        // { 'A': [...], 'B': [...], ... }
var _glossaryActiveLetter = null;
var _glossarySearchTimer = null;
var _glossaryLoading = false;

// 렌더링 제한
var GLOSSARY_MAX_ROWS = 2000;

/**
 * JSON 로드 + 인덱스 빌드 (1회만, 이후 캐시)
 */
function initGlossary(callback) {
    if (_glossaryData) {
        callback(_glossaryData);
        return;
    }
    if (_glossaryLoading) return;
    _glossaryLoading = true;

    fetch('data/glossary.json?t=' + Date.now())
        .then(function(res) {
            if (!res.ok) throw new Error('용어집 데이터를 불러올 수 없습니다.');
            return res.json();
        })
        .then(function(data) {
            _glossaryData = data;
            _glossaryIndex = buildGlossaryIndex(data);
            _glossaryLoading = false;
            callback(data);
        })
        .catch(function(err) {
            _glossaryLoading = false;
            console.error('용어집 로드 오류:', err);
            var mainContent = document.getElementById('main-content');
            if (mainContent) {
                mainContent.innerHTML = '<h1>오류</h1><p>' + err.message + '</p>';
            }
        });
}

/**
 * abbr 첫 글자 기준으로 그룹핑
 */
function buildGlossaryIndex(data) {
    var index = {};
    for (var i = 0; i < data.length; i++) {
        var item = data[i];
        var letter = (item.abbr || '').charAt(0).toUpperCase();
        if (!letter || letter < 'A' || letter > 'Z') {
            letter = '#';
        }
        if (!index[letter]) index[letter] = [];
        index[letter].push(item);
    }
    return index;
}

/**
 * 용어집 페이지 전체 UI를 #main-content에 생성
 */
function renderGlossaryPage() {
    initGlossary(function() {
        var mainContent = document.getElementById('main-content');
        if (!mainContent) return;

        var totalCount = _glossaryData.length;

        // 페이지 구조 생성
        var html = '<div class="glossary-page">';

        // 제목
        html += '<h1 class="glossary-title">Aviation Glossary</h1>';

        // 툴바: 검색 + 통계
        html += '<div class="glossary-toolbar">';
        html += '<div class="glossary-search-wrap">';
        html += '<span class="glossary-search-icon"></span>';
        html += '<input type="text" id="glossary-search" placeholder="약어, 영문, 한국어로 검색..." autocomplete="off">';
        html += '<button id="glossary-search-clear" class="glossary-search-clear" title="Clear">&times;</button>';
        html += '</div>';
        html += '<span class="glossary-stats">' + totalCount.toLocaleString() + ' terms</span>';
        html += '</div>';

        // 알파벳 바
        html += '<div class="glossary-alphabet-bar" id="glossary-alphabet-bar">';
        html += renderAlphabetBar();
        html += '</div>';

        // 콘텐츠 영역
        html += '<div id="glossary-content" class="glossary-content">';
        html += '</div>';

        html += '</div>'; // .glossary-page

        mainContent.innerHTML = html;

        // 우측 패널 업데이트
        updateGlossaryNav();

        // 이벤트 바인딩
        bindGlossaryEvents();

        // 검색에서 진입한 경우 pending 처리, 아니면 초기 화면
        if (window._pendingGlossaryQuery) {
            var q = window._pendingGlossaryQuery;
            window._pendingGlossaryQuery = null;
            window._pendingGlossaryAbbr = null;
            var searchInput = document.getElementById('glossary-search');
            if (searchInput) searchInput.value = q;
            filterGlossary(q);
        } else if (window._pendingGlossaryAbbr) {
            var letter = window._pendingGlossaryAbbr.charAt(0).toUpperCase();
            window._pendingGlossaryAbbr = null;
            selectGlossaryLetter(letter);
        } else {
            renderGlossarySummary();
        }

        // content-panel 스크롤 위치 초기화
        var contentPanel = document.getElementById('content-panel');
        if (contentPanel) contentPanel.scrollTop = 0;
    });
}

/**
 * 알파벳 바 HTML 생성
 */
function renderAlphabetBar() {
    var letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('');
    var html = '';

    // "전체" 버튼
    html += '<button class="glossary-letter-btn' + (!_glossaryActiveLetter ? ' active' : '') + '" data-letter="ALL">All</button>';

    for (var i = 0; i < letters.length; i++) {
        var letter = letters[i];
        var count = (_glossaryIndex[letter] || []).length;
        var isActive = _glossaryActiveLetter === letter;
        var isEmpty = count === 0;

        html += '<button class="glossary-letter-btn';
        if (isActive) html += ' active';
        if (isEmpty) html += ' empty';
        html += '" data-letter="' + letter + '"';
        if (isEmpty) html += ' disabled';
        html += ' title="' + letter + ' (' + count + ')">';
        html += letter;
        html += '</button>';
    }

    // 숫자/기호 그룹
    var miscCount = (_glossaryIndex['#'] || []).length;
    if (miscCount > 0) {
        html += '<button class="glossary-letter-btn' + (_glossaryActiveLetter === '#' ? ' active' : '') + '" data-letter="#" title="# (' + miscCount + ')">#</button>';
    }

    return html;
}

/**
 * A-Z 카드 그리드 (초기 화면)
 */
function renderGlossarySummary() {
    var container = document.getElementById('glossary-content');
    if (!container) return;

    var letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('');
    var html = '<div class="glossary-letter-grid">';

    for (var i = 0; i < letters.length; i++) {
        var letter = letters[i];
        var items = _glossaryIndex[letter] || [];
        if (items.length === 0) continue;

        // 대표 항목 3개
        var previews = items.slice(0, 3);
        var previewHtml = '';
        for (var j = 0; j < previews.length; j++) {
            previewHtml += '<div class="glossary-card-item"><span class="glossary-card-abbr">' +
                escapeHtml(previews[j].abbr) + '</span> ' +
                escapeHtml(previews[j].en) + '</div>';
        }
        if (items.length > 3) {
            previewHtml += '<div class="glossary-card-more">+' + (items.length - 3) + ' more</div>';
        }

        html += '<div class="glossary-letter-card" data-letter="' + letter + '">';
        html += '<div class="glossary-card-header">';
        html += '<span class="glossary-card-letter">' + letter + '</span>';
        html += '<span class="glossary-card-count">' + items.length + '</span>';
        html += '</div>';
        html += '<div class="glossary-card-body">' + previewHtml + '</div>';
        html += '</div>';
    }

    html += '</div>';
    container.innerHTML = html;

    // 카드 클릭 이벤트
    container.querySelectorAll('.glossary-letter-card').forEach(function(card) {
        card.addEventListener('click', function() {
            selectGlossaryLetter(this.dataset.letter);
        });
    });
}

/**
 * 알파벳 선택 → 해당 그룹 테이블 렌더링
 */
function selectGlossaryLetter(letter) {
    _glossaryActiveLetter = letter === 'ALL' ? null : letter;

    // 알파벳 바 active 상태 업데이트
    var bar = document.getElementById('glossary-alphabet-bar');
    if (bar) {
        bar.innerHTML = renderAlphabetBar();
        bindAlphabetBarEvents();
    }

    // 우측 패널 active 상태 업데이트
    updateGlossaryNavActive();

    // 검색 입력 초기화
    var searchInput = document.getElementById('glossary-search');
    if (searchInput) searchInput.value = '';

    if (!_glossaryActiveLetter) {
        renderGlossarySummary();
        return;
    }

    var items = _glossaryIndex[letter] || [];
    renderGlossaryItems(items, '', letter);
}

/**
 * DocumentFragment로 테이블 렌더링
 */
function renderGlossaryItems(items, query, letterLabel) {
    var container = document.getElementById('glossary-content');
    if (!container) return;

    if (items.length === 0) {
        container.innerHTML = '<div class="glossary-empty">검색 결과가 없습니다.</div>';
        return;
    }

    var truncated = items.length > GLOSSARY_MAX_ROWS;
    var displayItems = truncated ? items.slice(0, GLOSSARY_MAX_ROWS) : items;

    // 헤더 정보
    var headerHtml = '<div class="glossary-result-header">';
    if (query) {
        headerHtml += '<span class="glossary-result-info">"<strong>' + escapeHtml(query) + '</strong>" 검색 결과: ' + items.length.toLocaleString() + '건</span>';
    } else if (letterLabel) {
        headerHtml += '<span class="glossary-result-info">' + escapeHtml(letterLabel) + ' — ' + items.length.toLocaleString() + '건</span>';
    }
    headerHtml += '</div>';

    // 테이블 구성
    var fragment = document.createDocumentFragment();

    // 헤더 div
    var headerDiv = document.createElement('div');
    headerDiv.innerHTML = headerHtml;
    fragment.appendChild(headerDiv.firstChild);

    // 테이블
    var table = document.createElement('table');
    table.className = 'glossary-table';

    // thead
    var thead = document.createElement('thead');
    thead.innerHTML = '<tr><th class="glossary-col-abbr">Abbreviation</th><th class="glossary-col-en">English</th><th class="glossary-col-ko">Korean</th></tr>';
    table.appendChild(thead);

    // tbody
    var tbody = document.createElement('tbody');
    for (var i = 0; i < displayItems.length; i++) {
        var item = displayItems[i];
        var tr = document.createElement('tr');

        var tdAbbr = document.createElement('td');
        tdAbbr.className = 'glossary-abbr';
        tdAbbr.innerHTML = query ? highlightGlossaryTerm(item.abbr, query) : escapeHtml(item.abbr);

        var tdEn = document.createElement('td');
        tdEn.className = 'glossary-en';
        tdEn.innerHTML = query ? highlightGlossaryTerm(item.en, query) : escapeHtml(item.en);

        var tdKo = document.createElement('td');
        tdKo.className = 'glossary-ko';
        tdKo.innerHTML = query ? highlightGlossaryTerm(item.ko || '', query) : escapeHtml(item.ko || '');

        tr.appendChild(tdAbbr);
        tr.appendChild(tdEn);
        tr.appendChild(tdKo);
        tbody.appendChild(tr);
    }
    table.appendChild(tbody);
    fragment.appendChild(table);

    // 제한 초과 안내
    if (truncated) {
        var notice = document.createElement('div');
        notice.className = 'glossary-truncated';
        notice.textContent = GLOSSARY_MAX_ROWS.toLocaleString() + '건까지 표시됩니다. 검색어를 입력하여 결과를 좁혀주세요.';
        fragment.appendChild(notice);
    }

    container.innerHTML = '';
    container.appendChild(fragment);
}

/**
 * 검색 필터 (300ms 디바운스)
 */
function filterGlossary(query) {
    query = (query || '').trim().toLowerCase();

    if (!query) {
        _glossaryActiveLetter = null;
        // 알파벳 바 상태 초기화
        var bar = document.getElementById('glossary-alphabet-bar');
        if (bar) {
            bar.innerHTML = renderAlphabetBar();
            bindAlphabetBarEvents();
        }
        updateGlossaryNavActive();
        renderGlossarySummary();
        return;
    }

    // 전체 선형 스캔
    var results = [];
    for (var i = 0; i < _glossaryData.length; i++) {
        var item = _glossaryData[i];
        if ((item.abbr && item.abbr.toLowerCase().indexOf(query) !== -1) ||
            (item.en && item.en.toLowerCase().indexOf(query) !== -1) ||
            (item.ko && item.ko.indexOf(query) !== -1)) {
            results.push(item);
        }
    }

    // 알파벳 바 active 해제
    _glossaryActiveLetter = null;
    var bar = document.getElementById('glossary-alphabet-bar');
    if (bar) {
        bar.innerHTML = renderAlphabetBar();
        bindAlphabetBarEvents();
    }
    updateGlossaryNavActive();

    renderGlossaryItems(results, query, null);
}

/**
 * 우측 패널에 A-Z 퀵링크 표시
 */
function updateGlossaryNav() {
    var sectionNav = document.getElementById('section-nav');
    if (!sectionNav) return;

    var letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('');
    var html = '<div class="glossary-nav">';
    html += '<div class="glossary-nav-title">Alphabet</div>';

    for (var i = 0; i < letters.length; i++) {
        var letter = letters[i];
        var count = (_glossaryIndex[letter] || []).length;
        var isActive = _glossaryActiveLetter === letter;
        var isEmpty = count === 0;

        html += '<a class="glossary-nav-letter';
        if (isActive) html += ' active';
        if (isEmpty) html += ' empty';
        html += '" data-letter="' + letter + '"';
        if (!isEmpty) html += ' href="#"';
        html += '>' + letter;
        if (!isEmpty) html += '<span class="glossary-nav-count">' + count + '</span>';
        html += '</a>';
    }

    html += '</div>';
    sectionNav.innerHTML = html;

    // 클릭 이벤트
    sectionNav.querySelectorAll('.glossary-nav-letter:not(.empty)').forEach(function(el) {
        el.addEventListener('click', function(e) {
            e.preventDefault();
            selectGlossaryLetter(this.dataset.letter);
            // 상단으로 스크롤
            var contentPanel = document.getElementById('content-panel');
            if (contentPanel) contentPanel.scrollTop = 0;
        });
    });
}

/**
 * 우측 패널 active 상태만 업데이트 (전체 리렌더링 없이)
 */
function updateGlossaryNavActive() {
    var sectionNav = document.getElementById('section-nav');
    if (!sectionNav) return;

    sectionNav.querySelectorAll('.glossary-nav-letter').forEach(function(el) {
        if (el.dataset.letter === _glossaryActiveLetter) {
            el.classList.add('active');
        } else {
            el.classList.remove('active');
        }
    });
}

/**
 * 검색어 하이라이팅
 */
function highlightGlossaryTerm(text, query) {
    if (!text || !query) return escapeHtml(text);

    var escaped = escapeHtml(text);
    var queryEscaped = escapeRegExp(query);
    var regex = new RegExp('(' + queryEscaped + ')', 'gi');
    return escaped.replace(regex, '<mark class="glossary-highlight">$1</mark>');
}

/**
 * 이벤트 바인딩
 */
function bindGlossaryEvents() {
    // 검색 입력
    var searchInput = document.getElementById('glossary-search');
    var searchClear = document.getElementById('glossary-search-clear');

    if (searchInput) {
        searchInput.addEventListener('input', function() {
            var val = this.value;
            clearTimeout(_glossarySearchTimer);
            _glossarySearchTimer = setTimeout(function() {
                filterGlossary(val);
            }, 300);
        });

        // Enter 키로 즉시 검색
        searchInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                clearTimeout(_glossarySearchTimer);
                filterGlossary(this.value);
            }
        });
    }

    if (searchClear) {
        searchClear.addEventListener('click', function() {
            var searchInput = document.getElementById('glossary-search');
            if (searchInput) {
                searchInput.value = '';
                filterGlossary('');
                searchInput.focus();
            }
        });
    }

    // 알파벳 바 클릭
    bindAlphabetBarEvents();
}

/**
 * 알파벳 바 버튼 이벤트 바인딩
 */
function bindAlphabetBarEvents() {
    var bar = document.getElementById('glossary-alphabet-bar');
    if (!bar) return;

    bar.querySelectorAll('.glossary-letter-btn:not([disabled])').forEach(function(btn) {
        btn.addEventListener('click', function() {
            selectGlossaryLetter(this.dataset.letter);
        });
    });
}

/**
 * HTML 이스케이프
 */
function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
              .replace(/"/g, '&quot;').replace(/'/g, '&#039;');
}

/**
 * 정규식 이스케이프
 */
function escapeRegExp(str) {
    return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/* ===================================
   본문 약어 하이라이트 + 클릭 팝업
   =================================== */

var _glossaryAbbrMap = null;     // { lowercase_abbr: [items] }
var _glossaryAbbrSet = null;     // Set of UPPERCASE abbreviations
var _glossaryLookupEl = null;    // 팝업 DOM 요소
var _glossaryObserver = null;    // IntersectionObserver

/**
 * 용어 조회 시스템 초기화 (앱 시작 시 1회)
 */
function initGlossaryLookup() {
    var contentPanel = document.getElementById('content-panel');
    if (!contentPanel) return;

    // .glossary-term 클릭 → 팝업 (이벤트 위임)
    contentPanel.addEventListener('click', function(e) {
        var term = e.target.closest('.glossary-term');
        if (term) {
            e.preventDefault();
            var abbr = term.dataset.abbr;
            if (abbr && _glossaryAbbrMap) {
                var items = _glossaryAbbrMap[abbr.toLowerCase()];
                if (items && items.length > 0) {
                    var rect = term.getBoundingClientRect();
                    showGlossaryLookup(items, abbr, rect);
                }
            }
            return;
        }
        // 팝업 외부 클릭 시 닫기 (팝업 내부가 아닌 경우)
        if (_glossaryLookupEl && !_glossaryLookupEl.contains(e.target)) {
            hideGlossaryLookup();
        }
    });

    // 팝업 외부 mousedown 닫기
    document.addEventListener('mousedown', function(e) {
        if (_glossaryLookupEl && !_glossaryLookupEl.contains(e.target) &&
            !e.target.closest('.glossary-term')) {
            hideGlossaryLookup();
        }
    });

    // ESC 키로 닫기
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && _glossaryLookupEl) {
            hideGlossaryLookup();
        }
    });

    // 스크롤 시 닫기
    contentPanel.addEventListener('scroll', function() {
        if (_glossaryLookupEl) hideGlossaryLookup();
    });
}

/**
 * abbreviation Map/Set 빌드 (1회)
 */
function buildGlossaryAbbrMap() {
    if (_glossaryAbbrMap) return;
    _glossaryAbbrMap = {};
    _glossaryAbbrSet = new Set();

    for (var i = 0; i < _glossaryData.length; i++) {
        var item = _glossaryData[i];
        var abbr = item.abbr;
        if (!abbr || abbr.length < 2) continue;

        var key = abbr.toLowerCase();
        if (!_glossaryAbbrMap[key]) _glossaryAbbrMap[key] = [];
        _glossaryAbbrMap[key].push(item);
        _glossaryAbbrSet.add(abbr.toUpperCase());
    }
}

/**
 * 콘텐츠 로드 후 약어 하이라이트 시작 (IntersectionObserver)
 */
function highlightGlossaryTermsInContent() {
    // 용어집 페이지에서는 비활성
    if (AppState.currentPage === 'glossary:terms') return;

    // 이전 옵저버 정리
    if (_glossaryObserver) {
        _glossaryObserver.disconnect();
        _glossaryObserver = null;
    }

    // 데이터 로드 후 처리
    initGlossary(function() {
        buildGlossaryAbbrMap();

        var contentPanel = document.getElementById('content-panel');
        if (!contentPanel) return;

        var sections = document.querySelectorAll('#main-content .content-section');

        if (sections.length === 0) {
            // 섹션 래핑 없는 콘텐츠: 직접 처리
            processGlossaryTermsInElement(document.getElementById('main-content'));
            return;
        }

        // IntersectionObserver: 뷰포트 근처 섹션만 지연 처리
        _glossaryObserver = new IntersectionObserver(function(entries) {
            entries.forEach(function(entry) {
                if (entry.isIntersecting && !entry.target.dataset.glossaryProcessed) {
                    entry.target.dataset.glossaryProcessed = 'true';
                    processGlossaryTermsInElement(entry.target);
                }
            });
        }, {
            root: contentPanel,
            rootMargin: '200px 0px'  // 뷰포트 200px 앞서 처리
        });

        sections.forEach(function(section) {
            _glossaryObserver.observe(section);
        });
    });
}

/**
 * 요소 내 텍스트 노드에서 약어를 찾아 <span class="glossary-term">으로 래핑
 */
function processGlossaryTermsInElement(element) {
    if (!element || !_glossaryAbbrSet || _glossaryAbbrSet.size === 0) return;

    // 텍스트 노드 수집
    var walker = document.createTreeWalker(
        element,
        NodeFilter.SHOW_TEXT,
        {
            acceptNode: function(node) {
                var parent = node.parentElement;
                if (!parent) return NodeFilter.FILTER_REJECT;
                var tag = parent.tagName;
                // script, style, code, pre, input, 이미 처리된 .glossary-term 건너뜀
                if (tag === 'SCRIPT' || tag === 'STYLE' || tag === 'CODE' ||
                    tag === 'PRE' || tag === 'INPUT' || tag === 'TEXTAREA' ||
                    parent.classList.contains('glossary-term') ||
                    parent.closest('.glossary-term')) {
                    return NodeFilter.FILTER_REJECT;
                }
                return NodeFilter.FILTER_ACCEPT;
            }
        }
    );

    var nodesToProcess = [];
    while (walker.nextNode()) {
        // 빠른 사전 체크: 대문자 2글자 이상 연속이 있는 텍스트만 수집
        if (/[A-Z]{2,}/.test(walker.currentNode.nodeValue)) {
            nodesToProcess.push(walker.currentNode);
        }
    }

    // 역순 처리 (인덱스 밀림 방지)
    for (var i = nodesToProcess.length - 1; i >= 0; i--) {
        wrapGlossaryTermsInNode(nodesToProcess[i]);
    }
}

/**
 * 단일 텍스트 노드에서 약어 매칭 → <span> 래핑
 */
function wrapGlossaryTermsInNode(textNode) {
    var text = textNode.nodeValue;
    // 대문자로 시작, 대문자/숫자/하이픈/슬래시로 구성된 2글자 이상 단어 경계 매칭
    var regex = /\b([A-Z][A-Z0-9\/_-]{1,})\b/g;
    var match;
    var lastIndex = 0;
    var fragments = [];
    var hasMatch = false;

    while ((match = regex.exec(text)) !== null) {
        var word = match[1];
        if (_glossaryAbbrSet.has(word.toUpperCase())) {
            hasMatch = true;
            // 매칭 앞 텍스트
            if (match.index > lastIndex) {
                fragments.push(document.createTextNode(text.substring(lastIndex, match.index)));
            }
            // 약어 <span> 래핑
            var span = document.createElement('span');
            span.className = 'glossary-term';
            span.textContent = word;
            span.dataset.abbr = word.toUpperCase();
            fragments.push(span);
            lastIndex = match.index + match[0].length;
        }
    }

    if (!hasMatch) return;

    // 나머지 텍스트
    if (lastIndex < text.length) {
        fragments.push(document.createTextNode(text.substring(lastIndex)));
    }

    // 원본 텍스트 노드를 fragments로 교체
    var parent = textNode.parentNode;
    for (var j = 0; j < fragments.length; j++) {
        parent.insertBefore(fragments[j], textNode);
    }
    parent.removeChild(textNode);
}

/**
 * 조회 팝업 표시
 */
function showGlossaryLookup(results, query, selectionRect) {
    hideGlossaryLookup();

    var popup = document.createElement('div');
    popup.className = 'glossary-lookup-popup';

    var html = '<div class="glossary-lookup-header">';
    html += '<span class="glossary-lookup-badge">용어집</span>';
    html += '<button class="glossary-lookup-close" onclick="hideGlossaryLookup()">&times;</button>';
    html += '</div>';
    html += '<div class="glossary-lookup-body">';

    for (var i = 0; i < results.length; i++) {
        var item = results[i];
        html += '<div class="glossary-lookup-item">';
        html += '<span class="glossary-lookup-abbr">' + escapeHtml(item.abbr) + '</span>';
        html += '<span class="glossary-lookup-en">' + escapeHtml(item.en) + '</span>';
        if (item.ko) {
            html += '<span class="glossary-lookup-ko">' + escapeHtml(item.ko) + '</span>';
        }
        html += '</div>';
    }

    html += '</div>';

    // 용어집 페이지 링크
    var escapedQuery = escapeHtml(query).replace(/'/g, "\\'");
    html += '<div class="glossary-lookup-footer">';
    html += '<a href="#" onclick="loadGlossaryFromLookup(\'' + escapedQuery + '\'); return false;">용어집에서 보기</a>';
    html += '</div>';

    popup.innerHTML = html;
    document.body.appendChild(popup);
    _glossaryLookupEl = popup;

    // 위치 계산
    positionGlossaryLookup(popup, selectionRect);

    // 애니메이션
    requestAnimationFrame(function() {
        popup.classList.add('visible');
    });
}

/**
 * 팝업 위치 계산: 대상 요소 기준 아래/위 배치
 */
function positionGlossaryLookup(popup, rect) {
    var popupWidth = 360;
    var gap = 8;

    // 가로: 대상 중앙 정렬 (뷰포트 벗어남 방지)
    var left = rect.left + (rect.width / 2) - (popupWidth / 2);
    left = Math.max(8, Math.min(left, window.innerWidth - popupWidth - 8));

    // 세로: 대상 아래
    var top = rect.bottom + gap;

    popup.style.left = left + 'px';
    popup.style.top = top + 'px';
    popup.style.width = popupWidth + 'px';

    // 아래 공간 부족 시 위로 배치
    requestAnimationFrame(function() {
        var popupRect = popup.getBoundingClientRect();
        if (popupRect.bottom > window.innerHeight - 8) {
            popup.style.top = (rect.top - popupRect.height - gap) + 'px';
        }
    });
}

/**
 * 팝업 닫기
 */
function hideGlossaryLookup() {
    if (_glossaryLookupEl) {
        _glossaryLookupEl.remove();
        _glossaryLookupEl = null;
    }
}

/**
 * 팝업에서 용어집 페이지로 이동
 */
function loadGlossaryFromLookup(query) {
    hideGlossaryLookup();
    window._pendingGlossaryQuery = query;
    loadContent('glossary:terms');
}
