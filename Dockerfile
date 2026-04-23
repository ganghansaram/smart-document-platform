# ── Smart Document Platform: Backend Image ──
# Python 3.11 + FastAPI + tools/ + pdf2zh + babeldoc ONNX
FROM python:3.11-slim AS base

# 시스템 의존성:
#  - 폰트(pdf2zh 렌더링 + 한글 LibreOffice 변환)
#  - libgl(OpenCV/OCR)
#  - libreoffice-writer(Plan-37 Phase 3 DOCX 전처리)
#  - libreoffice-script-provider-python(python3-uno bridge — UNO 매크로용)
#  - libpango/libharfbuzz(WeasyPrint — Compare 유사도 리포트 PDF 생성)
RUN apt-get update && apt-get install -y --no-install-recommends \
        fonts-liberation \
        fonts-dejavu-core \
        fonts-nanum \
        fonts-noto-cjk \
        libgl1 \
        libglib2.0-0 \
        libreoffice-writer \
        libreoffice-script-provider-python \
        libpango-1.0-0 \
        libharfbuzz0b \
        libpangoft2-1.0-0 \
    && rm -rf /var/lib/apt/lists/*

# ── 비특권 사용자 생성 (CIS Docker Benchmark, 보안 모범 관행) ──
# APP_UID/APP_GID는 빌드 시 호스트 사용자 UID와 일치시키기 위해 오버라이드 가능
# 예: docker build --build-arg APP_UID=1001 --build-arg APP_GID=1001 ...
ARG APP_UID=1000
ARG APP_GID=1000
RUN groupadd -g ${APP_GID} appuser \
    && useradd -u ${APP_UID} -g ${APP_GID} -m -s /bin/bash appuser

WORKDIR /app

# ── pip 의존성 (레이어 캐싱 최적화) — 루트로 설치 ──
# pdf2zh-next는 pymupdf<1.25.3을 요구하지만, 웹뷰 번역용 pymupdf4llm은 pymupdf==1.27.2가 필요함.
# 해결: pdf2zh-next 먼저 설치(의존성 포함) → pymupdf/pymupdf4llm만 1.27.x로 강제 업그레이드.
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt \
    && pip install --no-cache-dir --upgrade PyMuPDF==1.27.2 pymupdf4llm==1.27.2.1

# ── 앱 코드 ──
COPY backend/ /app/backend/
COPY tools/   /app/tools/

# backend/packages (윈도우 whl) 제거 — 이미 pip install 완료
RUN rm -rf /app/backend/packages

# ── 런타임 디렉토리 생성 및 소유권 설정 ──
# /app 전체를 appuser 소유로 변경 (볼륨 마운트 지점 제외 — 런타임에 호스트 권한 사용)
RUN mkdir -p /app/backend/temp /app/backend/logs \
    && chown -R appuser:appuser /app

# ── babeldoc 전체 캐시 다운로드 (appuser 권한) ──
# ONNX 모델 + CMap + 폰트 + tiktoken — 폐쇄망 배포 시 런타임 다운로드 불가하므로 빌드 시 포함
ENV HOME=/home/appuser
USER appuser
RUN python -c "\
from babeldoc.assets.assets import warmup; \
warmup(); \
print('babeldoc full cache ready (ONNX + fonts + CMap + tiktoken)')" || \
    echo "WARN: babeldoc cache failed — pdf2zh will not work in air-gapped environments"

WORKDIR /app/backend

EXPOSE 8000

CMD ["python", "main.py"]
