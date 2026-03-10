/* ===================================
   배너 슬라이드쇼
   =================================== */

// 배너 슬라이드 설정 (이미지 + 영상 혼합 가능)
// type: 'image' | 'video'
const bannerSlides = [
    { type: 'video', src: 'css/images/kf21_video_sample.mp4' },
    { type: 'image', src: 'css/images/1-1_KF-21.jpg' },
    { type: 'image', src: 'css/images/1-2_KF-21.jpg' },
    { type: 'image', src: 'css/images/1-3_KF-21.jpg' }
];

// 슬라이드쇼 설정
const slideConfig = {
    interval: 4000,       // 4초마다 전환 (이미지)
    fadeDuration: 1000,   // 1초 페이드 효과
    videoFadeOutBefore: 1.8  // 영상 종료 N초 전에 페이드아웃 시작
};

let currentSlide = 0;
let slideInterval = null;
let isTransitioning = false;

/**
 * 기존 슬라이드쇼 정리
 */
function cleanupSlideshow(banner) {
    // 기존 interval 정리
    if (slideInterval) {
        clearInterval(slideInterval);
        slideInterval = null;
    }

    // 기존 슬라이드 요소 제거
    const existingSlides = banner.querySelectorAll('.banner-slide');
    existingSlides.forEach(slide => slide.remove());

    // 기존 dots 제거
    const existingDots = banner.querySelector('.banner-dots');
    if (existingDots) {
        existingDots.remove();
    }
}

/**
 * 배너 슬라이드쇼 초기화
 */
function initBannerSlideshow() {
    const banner = document.getElementById('banner-slideshow');

    if (!banner || bannerSlides.length === 0) {
        return;
    }

    // 기존 슬라이드쇼 정리 (재초기화 시)
    cleanupSlideshow(banner);

    // 상태 초기화
    currentSlide = 0;
    isTransitioning = false;

    // 슬라이드 생성 (이미지 + 영상)
    bannerSlides.forEach((slideData, index) => {
        const slide = document.createElement('div');
        slide.className = 'banner-slide';
        slide.dataset.type = slideData.type;
        if (index === 0) slide.classList.add('active');

        if (slideData.type === 'video') {
            const video = document.createElement('video');
            video.src = slideData.src;
            video.muted = true;
            video.playsInline = true;
            video.preload = 'metadata';
            video.addEventListener('loadeddata', function() { this.classList.add('loaded'); });
            // 영상 종료 N초 전 미리 페이드아웃 시작
            video.addEventListener('timeupdate', function() {
                if (!isTransitioning && this.duration > 0 && this.currentTime > 1.0 &&
                    (this.duration - this.currentTime) <= slideConfig.videoFadeOutBefore) {
                    nextSlide();
                }
            });
            // 폴백: timeupdate가 놓쳤을 경우 ended로 처리
            video.addEventListener('ended', function() {
                if (!isTransitioning) nextSlide();
            });
            slide.appendChild(video);
        } else {
            const img = document.createElement('img');
            img.src = slideData.src;
            img.alt = 'KF-21 이미지 ' + (index + 1);
            img.onload = function() { this.classList.add('loaded'); };
            slide.appendChild(img);
        }

        banner.appendChild(slide);
    });

    // 점 네비게이션 생성
    if (bannerSlides.length > 1) {
        const dotsContainer = document.createElement('div');
        dotsContainer.className = 'banner-dots';

        bannerSlides.forEach((_, index) => {
            const dot = document.createElement('span');
            dot.className = 'banner-dot';
            if (index === 0) dot.classList.add('active');

            dot.addEventListener('click', () => {
                goToSlide(index);
            });

            dotsContainer.appendChild(dot);
        });

        banner.appendChild(dotsContainer);
    }

    // 첫 슬라이드가 영상이면 재생, 아니면 타이머 시작
    if (bannerSlides.length > 1) {
        activateSlideMedia(0);

        // 마우스 호버 시 일시정지
        banner.addEventListener('mouseenter', pauseSlideshow);
        banner.addEventListener('mouseleave', resumeSlideshow);
    }
}

/**
 * 슬라이드쇼 타이머 시작 (이미지 슬라이드용)
 */
function startSlideshow() {
    clearInterval(slideInterval);
    slideInterval = setInterval(() => {
        nextSlide();
    }, slideConfig.interval);
}

/**
 * 슬라이드쇼 일시정지 (호버 시)
 */
function pauseSlideshow() {
    clearInterval(slideInterval);
    // 영상은 호버해도 계속 재생 (이미지 타이머만 정지)
}

/**
 * 슬라이드쇼 재개 (호버 해제 시)
 */
function resumeSlideshow() {
    var slideData = bannerSlides[currentSlide];
    if (slideData && slideData.type === 'video') {
        var slide = document.querySelectorAll('.banner-slide')[currentSlide];
        var video = slide ? slide.querySelector('video') : null;
        if (video) video.play();
    } else {
        startSlideshow();
    }
}

/**
 * 슬라이드 미디어 활성화 (영상 재생 또는 타이머 시작)
 */
function activateSlideMedia(index) {
    var slideData = bannerSlides[index];
    if (slideData && slideData.type === 'video') {
        // 영상 슬라이드: 타이머 중지, 영상 재생 (끝나면 ended 이벤트로 전환)
        clearInterval(slideInterval);
        var slide = document.querySelectorAll('.banner-slide')[index];
        var video = slide ? slide.querySelector('video') : null;
        if (video) {
            video.currentTime = 0;
            video.play();
        }
    } else {
        // 이미지 슬라이드: 타이머 시작
        startSlideshow();
    }
}

/**
 * 다음 슬라이드
 */
function nextSlide() {
    if (isTransitioning) return;

    const nextIndex = (currentSlide + 1) % bannerSlides.length;
    goToSlide(nextIndex);
}

/**
 * 특정 슬라이드로 이동
 */
function goToSlide(index) {
    if (isTransitioning || index === currentSlide) return;

    const slides = document.querySelectorAll('.banner-slide');
    const dots = document.querySelectorAll('.banner-dot');

    if (slides.length === 0) {
        if (slideInterval) {
            clearInterval(slideInterval);
            slideInterval = null;
        }
        return;
    }

    isTransitioning = true;

    // 현재 슬라이드 비활성화 — 영상은 페이드 중에도 계속 재생, 완료 후 정지
    var prevIndex = currentSlide;
    var prevSlide = slides[prevIndex];
    prevSlide.classList.remove('active');
    if (prevSlide.dataset.type === 'video') {
        var prevVideo = prevSlide.querySelector('video');
        setTimeout(function() {
            if (prevVideo) prevVideo.pause();
        }, slideConfig.fadeDuration);
    }
    if (dots.length > 0) {
        dots[prevIndex].classList.remove('active');
    }

    // 다음 슬라이드 활성화
    currentSlide = index;
    slides[currentSlide].classList.add('active');
    if (dots.length > 0) {
        dots[currentSlide].classList.add('active');
    }

    // 페이드 완료 후 미디어 활성화 + 이전 영상 되감기
    setTimeout(() => {
        isTransitioning = false;
        // 페이드아웃 완료 후 되감기 (첫 프레임 노출 방지)
        if (prevSlide.dataset.type === 'video') {
            var v = prevSlide.querySelector('video');
            if (v) v.currentTime = 0;
        }
        activateSlideMedia(currentSlide);
    }, slideConfig.fadeDuration);
}

/**
 * 섹션 링크 + 통계 스트립 생성 (menu.json 기반)
 */
function generateSectionLinks() {
    var container = document.getElementById('section-links');
    if (!container) return;

    fetch('data/menu.json')
        .then(function(response) { return response.json(); })
        .then(function(menuData) {
            // 통계 스트립 생성
            generateHomeStats(menuData);

            // 1레벨 항목 중 children이 있는 것만
            var sections = menuData.filter(function(item) {
                return item.children && item.children.length > 0;
            });

            var descriptions = {
                '설계 기준': '구조·시스템·전장 설계 가이드라인',
                '규격 · 표준': 'MIL-STD, AS/EN, 사내 규격 모음',
                '시험 · 평가': '구조·환경·비행 시험 절차와 결과',
                '제조 · 공정': '복합재, 가공, 조립, 표면처리 기준',
                '품질 · 인증': '품질관리, 형상관리, 감항인증 문서',
                '운용 · 정비': '운용매뉴얼, 정비절차, ILS 자료',
                'KF-21 개발백서': 'KF-21 보라매 프로그램 개발 기록'
            };

            container.innerHTML = '';

            sections.forEach(function(section, idx) {
                var link = document.createElement('a');
                link.href = '#';

                // 마지막 카드이면서 3열에 1개만 남는 경우 전체 폭
                if (idx === sections.length - 1 && sections.length % 3 === 1) {
                    link.classList.add('section-link-full');
                }

                // 클릭 → 트리메뉴 해당 카테고리 펼치기
                var sectionLabel = section.label;
                link.onclick = function(e) {
                    e.preventDefault();
                    expandTreeToSection(sectionLabel);
                    return false;
                };

                var shortLabel = sectionLabel.replace(/\s*\(.*$/, '');
                var title = document.createElement('span');
                title.className = 'link-title';
                title.textContent = shortLabel;
                link.appendChild(title);

                var desc = document.createElement('span');
                desc.className = 'link-desc';
                desc.textContent = descriptions[shortLabel] || '';
                link.appendChild(desc);

                container.appendChild(link);
            });

        })
        .catch(function(error) {
            console.error('섹션 링크 생성 오류:', error);
        });
}

/**
 * 섹션 내 문서 수 계산 (재귀)
 */
function countDocumentsInSection(item) {
    var count = 0;
    if (item.url && !item.url.startsWith('glossary:')) count++;
    if (item.children) {
        for (var i = 0; i < item.children.length; i++) {
            count += countDocumentsInSection(item.children[i]);
        }
    }
    return count;
}

/**
 * 트리메뉴에서 해당 섹션을 찾아 펼치기
 */
function expandTreeToSection(sectionLabel) {
    var treeMenu = document.getElementById('tree-menu');
    if (!treeMenu) return;

    // 먼저 모든 항목 접기
    if (typeof collapseAllTree === 'function') collapseAllTree();

    // label로 트리 아이템 찾기
    var labels = treeMenu.querySelectorAll('.tree-label');
    for (var i = 0; i < labels.length; i++) {
        if (labels[i].textContent === sectionLabel) {
            var itemDiv = labels[i].closest('.tree-item');
            if (itemDiv && itemDiv.classList.contains('has-children')) {
                // 해당 항목 펼치기
                itemDiv.classList.add('expanded');
                var li = itemDiv.closest('li');
                if (li) {
                    var childMenu = li.querySelector('.child-menu');
                    if (childMenu) childMenu.classList.add('expanded');
                }
                // 스크롤하여 보이게
                itemDiv.scrollIntoView({ block: 'center', behavior: 'smooth' });
            }
            break;
        }
    }

    // 좌측 패널이 숨겨져 있으면 표시
    var leftPanel = document.getElementById('left-panel');
    if (leftPanel && leftPanel.classList.contains('hidden')) {
        var showLeft = document.getElementById('show-left');
        if (showLeft) showLeft.click();
    }
}

/**
 * 홈 통계 스트립 생성
 */
function generateHomeStats(menuData) {
    var existing = document.querySelector('.home-stats');
    if (existing) existing.remove();

    // 문서 수
    var docCount = 0;
    function countDocs(items) {
        for (var i = 0; i < items.length; i++) {
            if (items[i].url && !items[i].url.startsWith('glossary:')) docCount++;
            if (items[i].children) countDocs(items[i].children);
        }
    }
    countDocs(menuData);

    // 북마크 수
    var bookmarkCount = 0;
    try {
        var stored = localStorage.getItem('webbook-bookmarks');
        if (stored) bookmarkCount = JSON.parse(stored).length;
    } catch(e) {}

    var statsEl = document.createElement('div');
    statsEl.className = 'home-stats';

    var stats = [
        { icon: 'doc', value: docCount, label: '등록 문서' },
        { icon: 'bookmark', value: bookmarkCount, label: '내 북마크' }
    ];

    stats.forEach(function(stat) {
        var item = document.createElement('div');
        item.className = 'home-stat-item';
        item.appendChild(createStatIcon(stat.icon));

        var value = document.createElement('span');
        value.className = 'home-stat-value';
        value.textContent = stat.value;
        item.appendChild(value);

        var label = document.createElement('span');
        label.className = 'home-stat-label';
        label.textContent = stat.label;
        item.appendChild(label);

        statsEl.appendChild(item);
    });

    // 용어 수 비동기 로드
    var glossaryItem = document.createElement('div');
    glossaryItem.className = 'home-stat-item';

    if (typeof _glossaryData !== 'undefined' && _glossaryData) {
        glossaryItem.appendChild(createStatIcon('glossary'));
        var gVal = document.createElement('span');
        gVal.className = 'home-stat-value';
        gVal.textContent = _glossaryData.length.toLocaleString();
        glossaryItem.appendChild(gVal);
        var gLbl = document.createElement('span');
        gLbl.className = 'home-stat-label';
        gLbl.textContent = '항공 용어';
        glossaryItem.appendChild(gLbl);
        // 북마크 뒤에 삽입 (문서-용어-북마크 순서)
        statsEl.insertBefore(glossaryItem, statsEl.children[1]);
    } else {
        fetch('data/glossary.json?t=' + Date.now())
            .then(function(r) { return r.json(); })
            .then(function(data) {
                glossaryItem.appendChild(createStatIcon('glossary'));
                var val = document.createElement('span');
                val.className = 'home-stat-value';
                val.textContent = data.length.toLocaleString();
                glossaryItem.appendChild(val);
                var lbl = document.createElement('span');
                lbl.className = 'home-stat-label';
                lbl.textContent = '항공 용어';
                glossaryItem.appendChild(lbl);
                statsEl.insertBefore(glossaryItem, statsEl.children[1]);
            })
            .catch(function() {});
    }

    // 배너 바로 뒤에 삽입
    var banner = document.getElementById('banner-slideshow');
    if (banner && banner.nextSibling) {
        banner.parentNode.insertBefore(statsEl, banner.nextSibling);
    }
}

/**
 * 통계 아이콘 SVG
 */
function createStatIcon(type) {
    var svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('class', 'home-stat-icon');
    svg.setAttribute('viewBox', '0 0 24 24');
    svg.setAttribute('fill', 'none');
    svg.setAttribute('stroke', 'currentColor');
    svg.setAttribute('stroke-width', '2');
    svg.setAttribute('stroke-linecap', 'round');
    svg.setAttribute('stroke-linejoin', 'round');

    if (type === 'doc') {
        svg.innerHTML = '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>';
    } else if (type === 'glossary') {
        svg.innerHTML = '<path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>';
    } else if (type === 'bookmark') {
        svg.innerHTML = '<path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/>';
    }

    return svg;
}

/**
 * 첫 번째 자식 URL 찾기 (재귀)
 */
function findFirstChildUrl(item) {
    if (item.url) {
        return item.url;
    }
    if (item.children && item.children.length > 0) {
        return findFirstChildUrl(item.children[0]);
    }
    return null;
}

// 초기화는 app.js에서 홈 콘텐츠 로드 완료 후 호출 (DOMContentLoaded 중복 방지)
