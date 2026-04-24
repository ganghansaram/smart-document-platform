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
    clearInterval(toast._retryTimer);
    toast.textContent = message;
    toast.className = 'toast' + (type ? ' ' + type : '') + ' show';
    toast._timer = setTimeout(function () {
        toast.classList.remove('show');
    }, duration || 3000);
}

/**
 * 429 Retry-After 카운트다운 토스트 (Plan-44 Phase 4).
 * RequestGuard.fetchWithRetry 가 429 응답 받을 때 호출.
 * @param {number} secondsUntil  남은 대기 시간(초)
 */
function showRetryToast(secondsUntil) {
    var toast = document.getElementById('app-toast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'app-toast';
        toast.className = 'toast';
        document.body.appendChild(toast);
    }
    clearTimeout(toast._timer);
    clearInterval(toast._retryTimer);
    var remaining = Math.max(1, Math.floor(secondsUntil || 5));

    function tick() {
        toast.textContent = 'AI 서버 사용량이 많습니다. ' + remaining + '초 후 자동 재시도...';
        toast.className = 'toast warning show';
        remaining--;
        if (remaining < 0) {
            clearInterval(toast._retryTimer);
            toast._retryTimer = null;
            toast.classList.remove('show');
        }
    }
    tick();
    toast._retryTimer = setInterval(tick, 1000);
}
