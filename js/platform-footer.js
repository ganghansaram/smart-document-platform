/* ===================================
   공통 푸터 — initPlatformFooter(container)
   =================================== */

/**
 * @param {HTMLElement|string} container - 푸터를 삽입할 요소 또는 ID
 */
function initPlatformFooter(container) {
    var target = (typeof container === 'string')
        ? document.getElementById(container)
        : container;
    if (!target) return;

    var year = new Date().getFullYear();

    var footer = document.createElement('footer');
    footer.className = 'platform-footer';

    footer.innerHTML = '<div class="pf-inner">'
        + '<span class="pf-copyright">&copy; ' + year + ' Korea Aerospace Industries, Ltd.</span>'
        + '</div>';

    target.appendChild(footer);

    return footer;
}
