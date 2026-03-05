/* ===================================
   공통 푸터 — initPlatformFooter(container, options)
   =================================== */

/**
 * @param {HTMLElement|string} container - 푸터를 삽입할 요소 또는 ID
 * @param {Object} [options]
 * @param {boolean} [options.showContact] - 연락처(이메일/팀) 표시 (Explorer용)
 */
function initPlatformFooter(container, options) {
    var target = (typeof container === 'string')
        ? document.getElementById(container)
        : container;
    if (!target) return;

    options = options || {};
    var year = new Date().getFullYear();

    var footer = document.createElement('footer');
    footer.className = 'platform-footer';

    var inner = '<div class="pf-inner">';
    inner += '<span class="pf-copyright">&copy; ' + year + ' Korea Aerospace Industries, Ltd.</span>';

    if (options.showContact) {
        inner += '<span class="pf-contact">';
        inner += '디지털엔지니어링팀';
        inner += ' <span class="pf-divider">|</span> ';
        inner += '<a href="mailto:huiseok.ahn@koreaaero.com">huiseok.ahn@koreaaero.com</a>';
        inner += ' <span class="pf-divider">|</span> ';
        inner += 'Powered by <strong>WebBook</strong>';
        inner += '</span>';
    }

    inner += '</div>';
    footer.innerHTML = inner;
    target.appendChild(footer);

    return footer;
}
