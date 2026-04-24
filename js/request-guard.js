/* ===================================
   RequestGuard — 429 자동 재시도 fetch 래퍼 (Plan-44 Phase 4)
   =================================== */
(function (global) {
    'use strict';

    /**
     * fetch 래퍼 — 429 Too Many Requests 수신 시 Retry-After 만큼 대기 후 1회 자동 재시도.
     * 토스트 함수(showRetryToast)가 로드되어 있으면 카운트다운 표시.
     * 페이지 이탈 시 요청 중단은 브라우저의 fetch 기본 동작으로 처리됨.
     *
     * @param {string} url
     * @param {RequestInit} options   fetch 옵션 (signal 포함 가능)
     * @param {{maxRetries?: number}} [opts]
     * @returns {Promise<Response>}
     */
    async function fetchWithRetry(url, options, opts) {
        opts = opts || {};
        var maxRetries = opts.maxRetries == null ? 1 : opts.maxRetries;
        var attempt = 0;
        var response = await fetch(url, options);
        while (response.status === 429 && attempt < maxRetries) {
            attempt++;
            var retryAfter = parseInt(response.headers.get('Retry-After') || '5', 10);
            if (!isFinite(retryAfter) || retryAfter < 1) retryAfter = 5;
            if (typeof global.showRetryToast === 'function') {
                global.showRetryToast(retryAfter);
            }
            await new Promise(function (resolve) { setTimeout(resolve, retryAfter * 1000); });
            if (options && options.signal && options.signal.aborted) {
                throw new DOMException('Aborted during 429 retry', 'AbortError');
            }
            response = await fetch(url, options);
        }
        return response;
    }

    global.RequestGuard = { fetchWithRetry: fetchWithRetry };
})(window);
