/* ===================================
   공통 토스트 알림
   css/toast.css 와 함께 사용
   =================================== */

/**
 * 화면 하단 중앙에 토스트 메시지를 표시한다.
 * @param {string} message  표시할 텍스트
 * @param {string} [type]   'success' | 'error' | 'warning' (CSS 클래스)
 * @param {number} [duration=3000]  표시 시간 (ms)
 */
function showToast(message, type, duration) {
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
    toast._timer = setTimeout(function () {
        toast.classList.remove('show');
    }, duration || 3000);
}
