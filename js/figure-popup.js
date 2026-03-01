/* ===================================
   그림/표 참조 팝업 모달
   =================================== */

/**
 * 팝업 초기화 - 이벤트 위임 방식 (콘텐츠 동적 로드 호환)
 */
function initFigurePopup() {
    var overlay = document.getElementById('figure-popup-overlay');
    if (!overlay) return;

    // 콘텐츠 영역에서 [data-fig-ref] 클릭 감지 (이벤트 위임)
    var mainContent = document.getElementById('main-content');
    if (mainContent) {
        mainContent.addEventListener('click', function(e) {
            var refEl = e.target.closest('[data-fig-ref]');
            if (refEl) {
                e.preventDefault();
                var targetId = refEl.getAttribute('data-fig-ref');
                if (targetId) {
                    showFigurePopup(targetId);
                }
            }
        });
    }

    // 닫기 버튼
    var closeBtn = overlay.querySelector('.figure-popup-close');
    if (closeBtn) {
        closeBtn.addEventListener('click', closeFigurePopup);
    }

    // 배경 클릭으로 닫기
    overlay.addEventListener('click', function(e) {
        if (e.target === overlay) {
            closeFigurePopup();
        }
    });

    // ESC 키로 닫기
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && overlay.classList.contains('active')) {
            closeFigurePopup();
        }
    });
}

/**
 * 팝업 표시
 */
function showFigurePopup(targetId) {
    var overlay = document.getElementById('figure-popup-overlay');
    var body = overlay.querySelector('.figure-popup-body');
    var caption = overlay.querySelector('.figure-popup-caption');
    if (!overlay || !body) return;

    // 대상 요소 찾기
    var targetEl = document.getElementById(targetId);
    if (!targetEl) {
        console.warn('[figure-popup] Target not found:', targetId);
        return;
    }

    // 모달 폭을 본문 텍스트 폭에 맞추기 (max-width: 900px 영역)
    var mainContent = document.querySelector('.main-content');
    var modal = overlay.querySelector('.figure-popup-modal');
    if (mainContent && modal) {
        var firstChild = mainContent.querySelector(':scope > *');
        var textWidth = firstChild ? firstChild.offsetWidth : mainContent.offsetWidth;
        modal.style.width = textWidth + 'px';
    }

    // 본문 초기화
    body.innerHTML = '';

    // 대상에서 이미지 또는 표 추출
    var content = extractFigureContent(targetEl);

    if (content.html) {
        body.innerHTML = content.html;
    }

    // 캡션 설정
    caption.textContent = content.caption || targetId;

    // 헤더의 "원본 위치로 이동" 링크 갱신
    var gotoLink = overlay.querySelector('.figure-popup-goto');
    if (gotoLink) {
        gotoLink.onclick = function() {
            closeFigurePopup();
            var target = document.getElementById(targetId);
            if (target && typeof scrollToElementReliably === 'function') {
                scrollToElementReliably(target);
            } else if (target) {
                target.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        };
    }

    // 표시
    overlay.classList.add('active');
}

/**
 * 팝업 닫기
 */
function closeFigurePopup() {
    var overlay = document.getElementById('figure-popup-overlay');
    if (overlay) {
        overlay.classList.remove('active');
    }
}

/**
 * 대상 요소에서 이미지/표 콘텐츠 및 캡션 추출
 *
 * ID가 부여된 요소를 기준으로:
 * - 해당 요소 내부 또는 인접한 img/table을 찾음
 * - 캡션 텍스트 추출
 */
function extractFigureContent(el) {
    var result = { html: '', caption: '' };

    // 이미지 HTML 생성
    function imgHtml(imgEl) {
        return '<img src="' + imgEl.src + '" alt="' + (imgEl.alt || '') + '">';
    }

    // 표 HTML 생성
    function tblHtml(tblEl) {
        return tblEl.outerHTML;
    }

    // 1) 요소 자체가 img인 경우
    if (el.tagName === 'IMG') {
        result.html = imgHtml(el);
        result.caption = findCaption(el);
        return result;
    }

    // 2) 요소 자체가 table인 경우
    if (el.tagName === 'TABLE') {
        result.html = tblHtml(el);
        result.caption = findCaption(el);
        return result;
    }

    // 3) 요소 내부에서 img 찾기
    var img = el.querySelector('img');
    if (img) {
        result.html = imgHtml(img);
        result.caption = findCaption(el) || el.textContent.trim();
        return result;
    }

    // 4) 요소 내부에서 table 찾기
    var table = el.querySelector('table');
    if (table) {
        result.html = tblHtml(table);
        result.caption = findCaption(el) || el.textContent.trim();
        return result;
    }

    // 5) 양방향 인접 형제 탐색 → 가장 가까운 img/table 선택
    //    (캡션이 표 아래에 오는 경우와 위에 오는 경우 모두 대응)
    var candidates = [];
    var sibling, i;

    // 이전 형제 탐색
    sibling = el.previousElementSibling;
    for (i = 0; i < 3 && sibling; i++) {
        img = sibling.querySelector('img') || (sibling.tagName === 'IMG' ? sibling : null);
        if (img) { candidates.push({ type: 'img', el: img, dist: i + 1 }); break; }
        table = sibling.querySelector('table') || (sibling.tagName === 'TABLE' ? sibling : null);
        if (table) { candidates.push({ type: 'tbl', el: table, dist: i + 1 }); break; }
        sibling = sibling.previousElementSibling;
    }

    // 다음 형제 탐색
    sibling = el.nextElementSibling;
    for (i = 0; i < 3 && sibling; i++) {
        img = sibling.querySelector('img') || (sibling.tagName === 'IMG' ? sibling : null);
        if (img) { candidates.push({ type: 'img', el: img, dist: i + 1 }); break; }
        table = sibling.querySelector('table') || (sibling.tagName === 'TABLE' ? sibling : null);
        if (table) { candidates.push({ type: 'tbl', el: table, dist: i + 1 }); break; }
        sibling = sibling.nextElementSibling;
    }

    // 가장 가까운 후보 선택 (동일 거리면 이전 형제 우선 — 캡션이 표 아래인 경우)
    if (candidates.length > 0) {
        candidates.sort(function(a, b) { return a.dist - b.dist; });
        var best = candidates[0];
        result.html = best.type === 'img' ? imgHtml(best.el) : tblHtml(best.el);
        result.caption = el.textContent.trim();
        return result;
    }

    // 찾지 못한 경우 요소 텍스트 표시
    result.caption = el.textContent.trim();
    result.html = '<p style="color: var(--medium-gray); padding: 40px;">콘텐츠를 찾을 수 없습니다.</p>';
    return result;
}

/**
 * 캡션 텍스트 찾기 (인접 요소에서 Figure/Table/그림/표 패턴)
 */
function findCaption(el) {
    var captionPattern = /^(Figure|Table|그림|표)\s*\d/i;

    // 이전 형제에서 캡션 찾기
    var prev = el.previousElementSibling;
    for (var i = 0; i < 3 && prev; i++) {
        var text = prev.textContent.trim();
        if (captionPattern.test(text)) {
            return text;
        }
        prev = prev.previousElementSibling;
    }

    // 다음 형제에서 캡션 찾기
    var next = el.nextElementSibling;
    for (var j = 0; j < 3 && next; j++) {
        var text2 = next.textContent.trim();
        if (captionPattern.test(text2)) {
            return text2;
        }
        next = next.nextElementSibling;
    }

    return '';
}

// DOM 로드 후 초기화
document.addEventListener('DOMContentLoaded', initFigurePopup);
