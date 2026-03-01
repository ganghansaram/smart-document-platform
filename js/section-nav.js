/* ===================================
   섹션 네비게이터 (우측 목차)
   =================================== */

// 캐싱된 헤딩 요소 및 링크
var _cachedHeadingEls = [];
var _cachedLinks = [];

// 자동 추적 활성화 상태
var _autoTrackEnabled = false;

// 생성된 ID 추적 (중복 방지)
var _generatedIds = new Set();

/**
 * 섹션 ID 생성 (인덱싱 스크립트와 동일한 로직)
 */
function generateSectionId(title) {
    // 한글/영문/숫자/하이픈만 유지, 공백은 하이픈으로
    var id = title.replace(/[^\w\s가-힣-]/g, '')
                  .replace(/\s+/g, '-')
                  .trim()
                  .toLowerCase()
                  .substring(0, 50);

    if (!id) {
        id = 'section';
    }

    // 중복 방지
    var baseId = id;
    var counter = 1;
    while (_generatedIds.has(id)) {
        id = baseId + '-' + counter;
        counter++;
    }

    _generatedIds.add(id);
    return id;
}

/**
 * 섹션 네비게이터 업데이트
 */
function updateSectionNav() {
    var mainContent = document.getElementById('main-content');
    var sectionNav = document.getElementById('section-nav');

    // ID 추적 초기화
    _generatedIds.clear();

    // 모든 제목 요소 수집 (h1 ~ h6)
    var headings = mainContent.querySelectorAll('h1, h2, h3, h4, h5, h6');

    if (headings.length === 0) {
        sectionNav.innerHTML = '<p style="padding: 20px; color: #7f8c8d; font-size: 13px;">목차가 없습니다</p>';
        return;
    }

    // ID 자동 생성 (제목 기반, 인덱싱과 동일한 로직)
    for (var i = 0; i < headings.length; i++) {
        if (!headings[i].id) {
            var newId = generateSectionId(headings[i].textContent);
            headings[i].id = newId;
        } else {
            // 기존 ID도 추적에 추가
            _generatedIds.add(headings[i].id);
        }
    }

    // 헤딩을 계층적 트리 구조로 변환
    var tree = buildHeadingTree(headings);

    // 트리를 DOM으로 렌더링
    var ul = renderTree(tree, 0);

    sectionNav.innerHTML = '';
    sectionNav.appendChild(ul);

    // 헤딩 위치 및 링크 캐싱 후 스크롤 추적 시작
    cacheHeadingPositions();
    trackActiveSection();
}

/**
 * 헤딩 배열을 계층적 트리 구조로 변환
 */
function buildHeadingTree(headings) {
    var root = { children: [] };
    var stack = [{ node: root, level: 0 }];

    for (var i = 0; i < headings.length; i++) {
        var heading = headings[i];
        var level = parseInt(heading.tagName.substring(1));

        var newNode = {
            id: heading.id,
            text: heading.textContent,
            level: level,
            children: []
        };

        // 현재 레벨보다 높거나 같은 레벨이 나올 때까지 스택에서 제거
        while (stack.length > 1 && stack[stack.length - 1].level >= level) {
            stack.pop();
        }

        // 부모에 자식으로 추가
        stack[stack.length - 1].node.children.push(newNode);

        // 스택에 추가
        stack.push({ node: newNode, level: level });
    }

    return root.children;
}

/**
 * 트리를 DOM으로 렌더링 (재귀)
 */
function renderTree(nodes, depth) {
    var ul = document.createElement('ul');
    if (depth > 0) {
        ul.className = 'children-group';
    }

    for (var i = 0; i < nodes.length; i++) {
        var node = nodes[i];
        var li = document.createElement('li');

        var a = document.createElement('a');
        a.href = '#' + node.id;
        a.setAttribute('data-id', node.id);
        a.title = node.text;

        // 토글 아이콘 (좌측 패널과 동일한 구조)
        var toggleIcon = document.createElement('span');
        toggleIcon.className = 'toggle-icon';
        a.appendChild(toggleIcon);

        // 텍스트
        var textSpan = document.createElement('span');
        textSpan.className = 'item-text';
        textSpan.textContent = node.text;
        a.appendChild(textSpan);

        // 텍스트 클릭 → 섹션으로 스크롤
        (function(nodeId) {
            textSpan.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                scrollToSection(nodeId);
            });
        })(node.id);

        // 링크 기본 동작 방지
        a.addEventListener('click', function(e) {
            e.preventDefault();
        });

        if (node.children.length > 0) {
            a.classList.add('has-children');

            var childrenUl = renderTree(node.children, depth + 1);

            // 화살표 클릭 → 펼침/접힘만
            (function(link, childUl) {
                toggleIcon.addEventListener('click', function(e) {
                    e.preventDefault();
                    e.stopPropagation();
                    toggleChildren(link, childUl);
                });
            })(a, childrenUl);

            li.appendChild(a);
            li.appendChild(childrenUl);
        } else {
            li.appendChild(a);
        }

        ul.appendChild(li);
    }

    return ul;
}

/**
 * 헤딩 위치와 네비게이션 링크를 캐싱
 */
function cacheHeadingPositions() {
    var mainContent = document.getElementById('main-content');
    var sectionNav = document.getElementById('section-nav');
    if (!mainContent || !sectionNav) return;

    // 헤딩 요소 캐싱 (위치는 스크롤 시 동적으로 계산)
    _cachedHeadingEls = Array.from(mainContent.querySelectorAll('h1, h2, h3, h4, h5, h6'));

    _cachedLinks = [];
    var links = sectionNav.querySelectorAll('a');
    for (var j = 0; j < links.length; j++) {
        _cachedLinks.push({
            el: links[j],
            href: links[j].getAttribute('href')
        });
    }
}

/**
 * 섹션 목차 모두 펼치기
 */
function expandAllSections() {
    var sectionNav = document.getElementById('section-nav');
    if (!sectionNav) return;
    var items = sectionNav.querySelectorAll('.has-children');
    for (var i = 0; i < items.length; i++) {
        items[i].classList.add('expanded');
    }
    var groups = sectionNav.querySelectorAll('.children-group');
    for (var j = 0; j < groups.length; j++) {
        groups[j].classList.add('expanded');
    }
}

/**
 * 섹션 목차 모두 접기
 */
function collapseAllSections() {
    var sectionNav = document.getElementById('section-nav');
    if (!sectionNav) return;
    var items = sectionNav.querySelectorAll('.has-children');
    for (var i = 0; i < items.length; i++) {
        items[i].classList.remove('expanded');
    }
    var groups = sectionNav.querySelectorAll('.children-group');
    for (var j = 0; j < groups.length; j++) {
        groups[j].classList.remove('expanded');
    }
}

/**
 * 하위 그룹 토글
 */
function toggleChildren(toggleLink, childrenUl) {
    var isExpanded = toggleLink.classList.contains('expanded');
    if (isExpanded) {
        toggleLink.classList.remove('expanded');
        childrenUl.classList.remove('expanded');
    } else {
        toggleLink.classList.add('expanded');
        childrenUl.classList.add('expanded');
    }
}

/**
 * 특정 링크와 자식 그룹 펼치기
 */
function expandNode(link, childrenUl) {
    if (link) link.classList.add('expanded');
    if (childrenUl) childrenUl.classList.add('expanded');
}

/**
 * 섹션으로 스크롤
 */
function scrollToSection(sectionId) {
    var section = document.getElementById(sectionId);

    if (section) {
        scrollToElementReliably(section);

        // 클릭한 섹션 하이라이트 (auto-track 상태와 무관)
        setActiveSection(sectionId);
    }
}

/**
 * 특정 섹션을 활성 상태로 설정
 */
function setActiveSection(sectionId) {
    var sectionNav = document.getElementById('section-nav');
    if (!sectionNav) return;

    // 기존 active 제거
    var allLinks = sectionNav.querySelectorAll('a');
    for (var i = 0; i < allLinks.length; i++) {
        allLinks[i].classList.remove('active');
    }

    // 해당 섹션 active 추가
    var targetLink = sectionNav.querySelector('a[href="#' + sectionId + '"]');
    if (targetLink) {
        targetLink.classList.add('active');
        expandPathToActive(targetLink);
    }
}

/**
 * 스크롤 위치에 따라 활성 섹션 추적
 */
function trackActiveSection() {
    var contentPanel = document.getElementById('content-panel');
    if (!contentPanel) return;

    contentPanel.removeEventListener('scroll', onContentScroll);
    contentPanel.addEventListener('scroll', onContentScroll);
}

/**
 * 자동 추적 토글
 */
function toggleAutoTrack() {
    _autoTrackEnabled = !_autoTrackEnabled;
    var btn = document.getElementById('toggle-auto-track');
    if (btn) {
        var icon = btn.querySelector('.icon');
        if (_autoTrackEnabled) {
            btn.classList.add('active');
            btn.title = 'Auto Track: ON';
            if (icon) {
                icon.classList.remove('icon-auto-track-off');
                icon.classList.add('icon-auto-track-on');
            }
        } else {
            btn.classList.remove('active');
            btn.title = 'Auto Track: OFF';
            if (icon) {
                icon.classList.remove('icon-auto-track-on');
                icon.classList.add('icon-auto-track-off');
            }
        }
    }
}

/**
 * 콘텐츠 스크롤 이벤트 핸들러
 */
function onContentScroll() {
    if (!_autoTrackEnabled) return;

    var contentPanel = document.getElementById('content-panel');
    if (!contentPanel || _cachedHeadingEls.length === 0) return;

    var activeId = null;

    // 스크롤 시 동적으로 위치 계산 (content-visibility:auto 호환)
    var panelTop = contentPanel.getBoundingClientRect().top;
    for (var i = 0; i < _cachedHeadingEls.length; i++) {
        var rect = _cachedHeadingEls[i].getBoundingClientRect();
        if (rect.top - panelTop <= 100) {
            activeId = _cachedHeadingEls[i].id;
        }
    }

    if (activeId) {
        var activeLink = null;

        // 활성 상태 업데이트
        for (var j = 0; j < _cachedLinks.length; j++) {
            if (_cachedLinks[j].href === '#' + activeId) {
                _cachedLinks[j].el.classList.add('active');
                activeLink = _cachedLinks[j].el;
            } else {
                _cachedLinks[j].el.classList.remove('active');
            }
        }

        // 활성 항목의 상위 경로 펼치기 (기존 펼침 상태 유지)
        if (activeLink) {
            expandPathToActive(activeLink);

            // 활성 항목이 우측 패널에 보이도록 자동 스크롤
            var rightPanel = document.getElementById('right-panel');
            if (rightPanel) {
                var linkRect = activeLink.getBoundingClientRect();
                var panelRect = rightPanel.getBoundingClientRect();

                if (linkRect.top < panelRect.top || linkRect.bottom > panelRect.bottom) {
                    activeLink.scrollIntoView({ block: 'center', behavior: 'smooth' });
                }
            }
        }
    }
}

/**
 * 활성 항목의 상위 경로 펼치기 (기존 펼침 상태 유지)
 */
function expandPathToActive(activeLink) {
    var sectionNav = document.getElementById('section-nav');
    if (!sectionNav) return;

    // 활성 링크부터 상위로 올라가며 경로 펼치기 (다른 항목은 건드리지 않음)
    var current = activeLink;
    while (current && current !== sectionNav) {
        if (current.classList.contains('has-children')) {
            current.classList.add('expanded');
            var nextSibling = current.nextElementSibling;
            if (nextSibling && nextSibling.classList.contains('children-group')) {
                nextSibling.classList.add('expanded');
            }
        }
        if (current.classList.contains('children-group')) {
            current.classList.add('expanded');
            var prevSibling = current.previousElementSibling;
            if (prevSibling && prevSibling.classList.contains('has-children')) {
                prevSibling.classList.add('expanded');
            }
        }
        current = current.parentElement;
    }
}
