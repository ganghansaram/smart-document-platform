"""
로깅 설정 — RotatingFileHandler + 구조화 포맷

사용법:
    from logging_config import setup_logging
    setup_logging()  # 서버 시작 시 1회 호출
"""
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging(log_dir: str = "logs", level: str = "INFO"):
    """
    구조화 로깅 초기화.

    - 파일: {log_dir}/app.log (10MB x 5 로테이션)
    - 콘솔: stderr 출력
    - 포맷: 2026-03-31 12:00:00 [INFO] services.translator_service: 메시지
    """
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 파일 핸들러 (10MB x 5 로테이션)
    file_handler = RotatingFileHandler(
        log_path / "app.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    # 콘솔 핸들러
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # 중복 핸들러 방지
    if not root.handlers:
        root.addHandler(file_handler)
        root.addHandler(console_handler)
