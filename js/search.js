/* ===================================
   검색 기능
   =================================== */

/**
 * 검색 초기화
 */
function initSearch() {
    const searchTrigger = document.getElementById('search-trigger');
    const searchOverlay = document.getElementById('search-overlay');
    const searchClose = document.getElementById('search-close');
    const searchInput = document.getElementById('search-input');

    // 검색 오버레이 열기
    if (searchTrigger) {
        searchTrigger.addEventListener('click', function(e) {
            e.preventDefault();
            openSearchOverlay();
        });
    }

    // 검색 오버레이 닫기
    if (searchClose) {
        searchClose.addEventListener('click', function() {
            closeSearchOverlay();
        });
    }

    // 오버레이 배경 클릭 시 닫기
    if (searchOverlay) {
        searchOverlay.addEventListener('click', function(e) {
            if (e.target === searchOverlay) {
                closeSearchOverlay();
            }
        });
    }

    // ESC 키로 닫기
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && searchOverlay.classList.contains('active')) {
            closeSearchOverlay();
        }
    });

    // 검색 입력 이벤트
    if (searchInput) {
        let searchTimeout;
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                performSearch(searchInput.value);
            }, 300); // 300ms 디바운스
        });
    }

    // 검색 인덱스 로드
    loadSearchIndex();
}

/**
 * 검색 오버레이 열기
 */
function openSearchOverlay() {
    const searchOverlay = document.getElementById('search-overlay');
    const searchInput = document.getElementById('search-input');

    searchOverlay.classList.add('active');
    searchInput.focus();
    searchInput.value = '';
    document.getElementById('search-results').innerHTML = '';
}

/**
 * 검색 오버레이 닫기
 */
function closeSearchOverlay() {
    const searchOverlay = document.getElementById('search-overlay');
    searchOverlay.classList.remove('active');
}

/**
 * 검색 인덱스 로드
 */
function loadSearchIndex() {
    fetch('data/search-index.json?t=' + Date.now())
        .then(response => {
            if (!response.ok) {
                console.warn('검색 인덱스를 찾을 수 없습니다. 검색 기능이 제한됩니다.');
                return null;
            }
            return response.json();
        })
        .then(data => {
            if (data) {
                AppState.searchIndex = data;
                console.log('검색 인덱스 로드 완료:', data.length, '개 문서');
            }
        })
        .catch(error => {
            console.error('검색 인덱스 로드 오류:', error);
        });
}

/**
 * 검색 수행
 */
function performSearch(query) {
    const searchResults = document.getElementById('search-results');

    // 검색어가 비어있으면 초기화
    if (!query || query.trim().length < 2) {
        searchResults.innerHTML = '';
        return;
    }

    // 검색어 정규화
    const normalizedQuery = query.toLowerCase().trim();

    // 용어집 검색
    var glossaryMatches = searchGlossary(normalizedQuery);

    // 문서 검색
    var docResults = [];
    if (AppState.searchIndex && AppState.searchIndex.length > 0) {
        docResults = searchInIndex(normalizedQuery);
    }

    // 결과 표시
    displaySearchResults(docResults, query, glossaryMatches);
}

/**
 * 용어집에서 검색 (최대 표시 3건, 전체 카운트 반환)
 */
function searchGlossary(query) {
    if (!_glossaryData && typeof initGlossary !== 'function') {
        return { items: [], total: 0 };
    }

    // 데이터 미로드 시 비동기 로드 후 재검색 트리거
    if (!_glossaryData) {
        initGlossary(function() {
            var searchInput = document.getElementById('search-input');
            if (searchInput && searchInput.value.trim().length >= 2) {
                performSearch(searchInput.value);
            }
        });
        return { items: [], total: 0 };
    }

    var results = [];
    for (var i = 0; i < _glossaryData.length; i++) {
        var item = _glossaryData[i];
        if ((item.abbr && item.abbr.toLowerCase().indexOf(query) !== -1) ||
            (item.en && item.en.toLowerCase().indexOf(query) !== -1) ||
            (item.ko && item.ko.indexOf(query) !== -1)) {
            results.push(item);
        }
    }

    // abbr 정확 매칭 우선 정렬
    results.sort(function(a, b) {
        var aExact = a.abbr.toLowerCase() === query ? 0 : 1;
        var bExact = b.abbr.toLowerCase() === query ? 0 : 1;
        return aExact - bExact;
    });

    return { items: results.slice(0, 3), total: results.length };
}

/**
 * 인덱스에서 검색
 */
function searchInIndex(query) {
    const results = [];

    AppState.searchIndex.forEach(doc => {
        const titleMatch = doc.title.toLowerCase().includes(query);
        const contentMatch = doc.content.toLowerCase().includes(query);

        if (titleMatch || contentMatch) {
            // 매칭된 텍스트 스니펫 추출
            const snippet = extractSnippet(doc.content, query);

            results.push({
                title: doc.title,
                url: doc.url,
                path: doc.path,
                snippet: snippet,
                sectionId: doc.section_id || null,
                score: titleMatch ? 10 : 1 // 제목 매칭이 더 높은 점수
            });
        }
    });

    // 점수순으로 정렬
    results.sort((a, b) => b.score - a.score);

    return results;
}

/**
 * 검색어 주변 텍스트 스니펫 추출
 */
function extractSnippet(content, query, maxLength = 150) {
    const lowerContent = content.toLowerCase();
    const queryIndex = lowerContent.indexOf(query.toLowerCase());

    if (queryIndex === -1) {
        // 검색어가 없으면 처음 150자 반환
        return content.substring(0, maxLength) + '...';
    }

    // 검색어 앞뒤로 컨텍스트 추출
    const start = Math.max(0, queryIndex - 50);
    const end = Math.min(content.length, queryIndex + query.length + 100);

    let snippet = content.substring(start, end);

    if (start > 0) snippet = '...' + snippet;
    if (end < content.length) snippet = snippet + '...';

    return snippet;
}

/**
 * 검색 결과 표시
 */
function displaySearchResults(results, query, glossaryMatches) {
    const searchResults = document.getElementById('search-results');
    const hasGlossary = glossaryMatches && glossaryMatches.total > 0;
    const hasDocs = results.length > 0;

    if (!hasGlossary && !hasDocs) {
        searchResults.innerHTML = `
            <div class="search-no-results">
                <p>검색 결과가 없습니다.</p>
                <p>"${escapeHtml(query)}"에 대한 결과를 찾을 수 없습니다.</p>
            </div>
        `;
        return;
    }

    let html = '';

    // 용어집 결과 (상단 그룹)
    if (hasGlossary) {
        html += '<div class="search-glossary-group">';
        html += '<div class="search-group-header">용어집 (' + glossaryMatches.total + '건)</div>';
        glossaryMatches.items.forEach(function(item) {
            html += '<div class="search-glossary-item" data-action="glossary" data-query="' + escapeHtml(item.en) + '">';
            html += '<span class="search-glossary-abbr">' + highlightSearchTerm(item.abbr, query) + '</span>';
            html += '<span class="search-glossary-en">' + highlightSearchTerm(item.en, query) + '</span>';
            if (item.ko) {
                html += '<span class="search-glossary-ko">' + highlightSearchTerm(item.ko, query) + '</span>';
            }
            html += '</div>';
        });
        if (glossaryMatches.total > 3) {
            html += '<div class="search-glossary-more" data-action="glossary" data-query="' + escapeHtml(query) + '">용어집에서 ' + glossaryMatches.total + '건 모두 보기</div>';
        }
        html += '</div>';
    }

    // 문서 결과
    if (hasDocs) {
        if (hasGlossary) {
            html += '<div class="search-group-header">문서 (' + results.length + '건)</div>';
        }
        results.forEach(function(result) {
            var highlightedSnippet = highlightSearchTerm(result.snippet, query);
            var sectionAttr = result.sectionId ? ' data-section="' + escapeHtml(result.sectionId) + '"' : '';

            html += '<div class="search-result-item" data-action="result" data-url="' + escapeHtml(result.url) + '"' + sectionAttr + ' data-query="' + escapeHtml(query) + '">';
            html += '<div class="search-result-title">' + escapeHtml(result.title) + '</div>';
            html += '<div class="search-result-path">' + escapeHtml(result.path) + '</div>';
            html += '<div class="search-result-snippet">' + highlightedSnippet + '</div>';
            html += '</div>';
        });
    }

    searchResults.innerHTML = html;

    // 이벤트 위임 (중복 방지: 리스너가 없을 때만 등록)
    if (!searchResults._delegated) {
        searchResults._delegated = true;
        searchResults.addEventListener('click', function(e) {
            var target = e.target.closest('[data-action]');
            if (!target) return;

            var action = target.getAttribute('data-action');
            if (action === 'glossary') {
                loadGlossaryFromSearch(null, target.getAttribute('data-query'));
            } else if (action === 'result') {
                loadSearchResult(
                    target.getAttribute('data-url'),
                    target.getAttribute('data-section') || null,
                    target.getAttribute('data-query')
                );
            }
        });
    }
}

/**
 * 검색에서 용어집으로 이동
 */
function loadGlossaryFromSearch(abbr, query) {
    closeSearchOverlay();

    // 용어집 로드 후 필터링할 값을 임시 저장
    window._pendingGlossaryQuery = query || null;
    window._pendingGlossaryAbbr = abbr || null;
    loadContent('glossary:terms');
}

/**
 * 검색 결과 로드
 */
function loadSearchResult(url, sectionId, query) {
    closeSearchOverlay();

    // 같은 페이지인 경우 스크롤만
    if (AppState.currentPage === url && sectionId) {
        scrollToSearchSection(sectionId);
        if (query) {
            highlightSearchTermsInContent(query);
        }
        return;
    }

    // 다른 페이지인 경우: 섹션 ID 및 검색어 설정 후 로드
    if (sectionId) {
        window._pendingScrollToSection = sectionId;
    }
    if (query) {
        window._pendingHighlightQuery = query;
    }
    loadContent(url);
}

/**
 * 검색 결과 섹션으로 스크롤
 */
function scrollToSearchSection(sectionId) {
    var targetEl = document.getElementById(sectionId);

    if (targetEl) {
        scrollToElementReliably(targetEl);
    }
}

/**
 * 콘텐츠 내 검색어 하이라이트
 */
function highlightSearchTermsInContent(query) {
    var mainContent = document.getElementById('main-content');
    if (!mainContent || !query) return;

    // 기존 하이라이트 제거
    removeSearchHighlights();

    // 텍스트 노드에서 검색어 찾아 하이라이트
    var regex = new RegExp('(' + escapeRegExp(query) + ')', 'gi');
    highlightTextNodes(mainContent, regex);

    // 페이드아웃 후 제거 (5초 후)
    setTimeout(function() {
        fadeOutSearchHighlights();
    }, 5000);
}

/**
 * 정규식 특수문자 이스케이프
 */
function escapeRegExp(string) {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/**
 * 텍스트 노드 순회하며 하이라이트 적용
 */
function highlightTextNodes(element, regex) {
    var walker = document.createTreeWalker(
        element,
        NodeFilter.SHOW_TEXT,
        null,
        false
    );

    var nodesToProcess = [];
    while (walker.nextNode()) {
        if (regex.test(walker.currentNode.nodeValue)) {
            nodesToProcess.push(walker.currentNode);
        }
        regex.lastIndex = 0; // reset regex
    }

    nodesToProcess.forEach(function(textNode) {
        var span = document.createElement('span');
        span.innerHTML = textNode.nodeValue.replace(regex, '<mark class="search-term-highlight">$1</mark>');
        textNode.parentNode.replaceChild(span, textNode);
    });
}

/**
 * 검색어 하이라이트 페이드아웃
 */
function fadeOutSearchHighlights() {
    var highlights = document.querySelectorAll('.search-term-highlight');
    highlights.forEach(function(el) {
        el.classList.add('fade-out');
    });

    // 애니메이션 완료 후 제거
    setTimeout(function() {
        removeSearchHighlights();
    }, 500);
}

/**
 * 검색어 하이라이트 제거
 */
function removeSearchHighlights() {
    var highlights = document.querySelectorAll('.search-term-highlight');
    highlights.forEach(function(el) {
        var parent = el.parentNode;
        parent.replaceChild(document.createTextNode(el.textContent), el);
        parent.normalize();
    });
}

/**
 * 검색어 하이라이트
 */
function highlightSearchTerm(text, query) {
    const escapedText = escapeHtml(text);
    const escapedQuery = escapeHtml(query);
    const regex = new RegExp(`(${escapedQuery})`, 'gi');
    return escapedText.replace(regex, '<mark>$1</mark>');
}

/**
 * HTML 이스케이프
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
