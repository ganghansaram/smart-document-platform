"""
CLI 관리 도구 — admin 계정 생성/조회
서버 없이 직접 DB 조작 (초기 세팅, 비상 복구)
"""
import sys
import os
import io
import getpass

# Windows cp949 인코딩 문제 방지
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# 프로젝트 루트 → backend를 import path에 추가
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "backend"))

import config
from services.auth import init_db, create_user, list_users


def main():
    print("=" * 50)
    print("  KF-21 WebBook — Admin 계정 관리")
    print("=" * 50)

    # DB 초기화
    init_db()

    # 기존 사용자 목록
    users = list_users()
    if users:
        print(f"\n기존 사용자 ({len(users)}명):")
        for u in users:
            print(f"  - {u['username']} (role: {u['role']}, id: {u['id']})")
    else:
        print("\n등록된 사용자가 없습니다.")

    # 새 계정 생성
    print("\n--- 새 admin 계정 생성 ---")
    username = input("Username: ").strip()
    if not username:
        print("취소됨.")
        return

    password = getpass.getpass("Password: ")
    if not password:
        print("취소됨.")
        return

    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        print("비밀번호가 일치하지 않습니다.")
        return

    try:
        user = create_user(username, password, "admin")
        print(f"\n✓ admin 계정 생성 완료: {user['username']} (id: {user['id']})")
    except Exception as e:
        if "UNIQUE" in str(e):
            print(f"\n✗ 이미 존재하는 username입니다: {username}")
        else:
            print(f"\n✗ 오류: {e}")


if __name__ == "__main__":
    main()
