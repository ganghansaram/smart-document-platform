/* ===================================
   RequestGuard — 429 자동 재시도 + 중복 요청 방어 (Plan-44 Phase 4)
   =================================== */
(function (global) {
    'use strict';

    // key -> { controller: AbortController, promise }
    var inFlight = {};

    /**
     * fetch 래퍼 — 429 Too Many Requests 수신 시 Retry-After 만큼 대기 후 1회 자동 재시도.
     * 토스트 함수(showRetryToast)가 로드되어 있으면 카운트다운 표시.
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
            // 기존 signal 이 abort 된 경우 재시도 중단
            if (options && options.signal && options.signal.aborted) {
                throw new DOMException('Aborted during 429 retry', 'AbortError');
            }
            response = await fetch(url, options);
        }
        return response;
    }

    /**
     * key 기반 중복 요청 방어. 동일 key 진행 중이면 기존 promise 재사용(기본) 또는 reject(dedupe='reject').
     * AbortController 를 factory 에 전달 — 호출부는 signal 을 fetch 에 연결.
     */
    function guard(key, factory, opts) {
        opts = opts || {};
        if (inFlight[key]) {
            if (opts.dedupe === 'reject') {
                return Promise.reject(new Error('request-guard: already in-flight (' + key + ')'));
            }
            return inFlight[key].promise;
        }
        var controller = new AbortController();
        var promise = Promise.resolve(factory(controller.signal))
            .finally(function () { delete inFlight[key]; });
        inFlight[key] = { controller: controller, promise: promise };
        return promise;
    }

    function abort(key) {
        var entry = inFlight[key];
        if (entry) {
            entry.controller.abort();
            delete inFlight[key];
        }
    }

    function abortAll() {
        Object.keys(inFlight).forEach(abort);
    }

    function isBusy(key) {
        return !!inFlight[key];
    }

    // 페이지 이탈·탭 종료 시 모든 요청 abort (서버 리소스 조기 해제)
    global.addEventListener('beforeunload', abortAll);

    global.RequestGuard = {
        fetchWithRetry: fetchWithRetry,
        guard: guard,
        abort: abort,
        abortAll: abortAll,
        isBusy: isBusy
    };
})(window);
