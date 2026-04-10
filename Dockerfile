# ── Smart Document Platform: Backend Image ──
# Python 3.11 + FastAPI + tools/ + pdf2zh + babeldoc ONNX
FROM python:3.11-slim AS base

# 시스템 의존성: 폰트(pdf2zh 렌더링), libgl(OpenCV/OCR)
RUN apt-get update && apt-get install -y --no-install-recommends \
        fonts-liberation \
        fonts-dejavu-core \
        libgl1 \
        libglib2.0-0 \
        libreoffice-writer \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── pip 의존성 (레이어 캐싱 최적화) ──
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt \
    && pip install --no-cache-dir --no-deps pdf2zh-next==2.8.2

# ── babeldoc ONNX 캐시 (폐쇄망 대응 — 방안 A: 이미지에 포함) ──
# 빌드 시 다운로드하여 이미지에 번들링 (~500MB)
# 런타임에 네트워크 불필요
RUN python -c "\
from babeldoc.docvision.doclayout import OnnxModel; \
OnnxModel.from_pretrained(); \
print('babeldoc ONNX model cached')" 2>/dev/null || \
    echo "WARN: babeldoc cache skipped (model download failed — will retry at runtime)"

# ── 앱 코드 ──
COPY backend/ /app/backend/
COPY tools/   /app/tools/

# backend/packages (윈도우 whl) 제거 — 이미 pip install 완료
RUN rm -rf /app/backend/packages

# ── 런타임 디렉토리 ──
RUN mkdir -p /app/backend/temp /app/backend/logs

WORKDIR /app/backend

EXPOSE 8000

CMD ["python", "main.py"]
