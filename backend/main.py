"""
FastAPI 백엔드 진입점
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import search, chat, document, upload, auth, analytics, settings, menu, translator
from services.auth import init_db
from services.analytics import init_db as init_analytics_db
from services.settings_service import apply_settings_on_startup
import config

app = FastAPI(title="KF-21 WebBook API")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(search.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(document.router, prefix="/api")
app.include_router(upload.router, prefix="/api")      # 문서 업로드/변환 API
app.include_router(auth.router, prefix="/api")         # 인증 API
app.include_router(analytics.router, prefix="/api")    # Analytics API
app.include_router(settings.router, prefix="/api")     # 관리자 설정 API
app.include_router(menu.router, prefix="/api")         # 메뉴 관리 API
app.include_router(translator.router, prefix="/api")    # Translator API

@app.on_event("startup")
def startup():
    init_db()
    init_analytics_db()
    apply_settings_on_startup()  # settings.json → config 적용

@app.get("/api/health")
def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.HOST, port=config.PORT)
