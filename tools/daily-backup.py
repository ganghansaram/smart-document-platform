#!/usr/bin/env python3
"""
일일 백업 스크립트 — Windows Task Scheduler 또는 cron으로 실행

사용법:
    python tools/daily-backup.py                    # 기본 (backups/ 디렉토리)
    python tools/daily-backup.py --dest D:\backups  # 외부 경로 지정
    python tools/daily-backup.py --retention 60     # 60일 보존

기능:
    1. SQLite DB 안전 백업 (auth.db, analytics.db)
    2. settings.json 복사
    3. translator 데이터 전체 미러 (증분 가능)
    4. 보존 기간 초과 백업 자동 삭제
    5. 백업 결과 로그
"""
import argparse
import shutil
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 프로젝트 루트 기준 경로
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DEFAULT_BACKUP_DIR = PROJECT_ROOT / "backups"
DEFAULT_RETENTION_DAYS = 30


def backup_sqlite(db_path: Path, dest_dir: Path) -> bool:
    """SQLite .backup API로 안전한 핫 백업"""
    if not db_path.exists():
        print(f"  [SKIP] {db_path.name} — 파일 없음")
        return True
    dest_path = dest_dir / db_path.name
    try:
        src_conn = sqlite3.connect(str(db_path))
        dst_conn = sqlite3.connect(str(dest_path))
        src_conn.backup(dst_conn)
        dst_conn.close()
        src_conn.close()
        size_kb = dest_path.stat().st_size / 1024
        print(f"  [OK] {db_path.name} ({size_kb:.0f} KB)")
        return True
    except Exception as e:
        print(f"  [ERROR] {db_path.name}: {e}")
        return False


def backup_file(src: Path, dest_dir: Path) -> bool:
    """단일 파일 복사"""
    if not src.exists():
        print(f"  [SKIP] {src.name} — 파일 없음")
        return True
    try:
        shutil.copy2(str(src), str(dest_dir / src.name))
        print(f"  [OK] {src.name}")
        return True
    except Exception as e:
        print(f"  [ERROR] {src.name}: {e}")
        return False


def backup_translator_data(dest_dir: Path) -> bool:
    """translator 데이터 디렉토리 미러 (copytree)"""
    src = DATA_DIR / "translator"
    if not src.exists():
        print("  [SKIP] translator/ — 디렉토리 없음")
        return True
    dest = dest_dir / "translator"
    try:
        if dest.exists():
            shutil.rmtree(str(dest))
        shutil.copytree(str(src), str(dest))
        # 파일 수 계산
        file_count = sum(1 for _ in dest.rglob("*") if _.is_file())
        size_mb = sum(f.stat().st_size for f in dest.rglob("*") if f.is_file()) / (1024 * 1024)
        print(f"  [OK] translator/ ({file_count}개 파일, {size_mb:.1f} MB)")
        return True
    except Exception as e:
        print(f"  [ERROR] translator/: {e}")
        return False


def cleanup_old_backups(backup_root: Path, retention_days: int):
    """보존 기간 초과 백업 디렉토리 삭제"""
    cutoff = datetime.now() - timedelta(days=retention_days)
    removed = 0
    for d in sorted(backup_root.iterdir()):
        if not d.is_dir():
            continue
        try:
            dir_date = datetime.strptime(d.name, "%Y-%m-%d")
            if dir_date < cutoff:
                shutil.rmtree(str(d))
                removed += 1
        except ValueError:
            continue  # 날짜 형식이 아닌 디렉토리 무시
    if removed:
        print(f"\n[CLEANUP] {removed}개 만료 백업 삭제 (>{retention_days}일)")


def main():
    parser = argparse.ArgumentParser(description="Smart Document Platform 일일 백업")
    parser.add_argument("--dest", type=str, default=str(DEFAULT_BACKUP_DIR),
                        help=f"백업 디렉토리 (기본: {DEFAULT_BACKUP_DIR})")
    parser.add_argument("--retention", type=int, default=DEFAULT_RETENTION_DAYS,
                        help=f"백업 보존 기간 (일, 기본: {DEFAULT_RETENTION_DAYS})")
    args = parser.parse_args()

    backup_root = Path(args.dest)
    today = datetime.now().strftime("%Y-%m-%d")
    dest_dir = backup_root / today
    dest_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== Smart Document Platform 백업 ===")
    print(f"날짜: {today}")
    print(f"대상: {dest_dir}")
    print()

    success = True

    # 1. SQLite DB
    print("[1/4] SQLite 데이터베이스")
    success &= backup_sqlite(DATA_DIR / "auth.db", dest_dir)
    success &= backup_sqlite(DATA_DIR / "analytics.db", dest_dir)
    print()

    # 2. Settings
    print("[2/4] 설정 파일")
    success &= backup_file(DATA_DIR / "settings.json", dest_dir)
    print()

    # 3. Translator 데이터
    print("[3/4] Translator 데이터")
    success &= backup_translator_data(dest_dir)
    print()

    # 4. 만료 백업 삭제
    print(f"[4/4] 만료 백업 정리 (보존: {args.retention}일)")
    cleanup_old_backups(backup_root, args.retention)

    print()
    if success:
        print("[DONE] 백업 완료")
    else:
        print("[WARN] 일부 항목 백업 실패 — 로그를 확인하세요")
        sys.exit(1)


if __name__ == "__main__":
    main()
