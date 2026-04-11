#!/usr/bin/env python3
"""
Docker Parity Check — 로컬 프로젝트 상태와 Docker 이미지가 담을 내용 사이의
divergence(불일치)를 빌드 전에 감지한다.

Plan-31 Phase 4의 산출물. Phase 2(COPY 블랙리스트 재구조화)의 원래 목적을
"명시적 경고" 방식으로 더 안전하게 달성한다.

## 검사 항목

1. **프론트엔드 자산 커버리지** — `docker/Dockerfile.nginx`의 COPY 패턴이
   프로젝트 루트의 프론트엔드 파일/폴더(*.html, favicon.svg, css/, js/,
   docs/, 그리고 미래의 fonts/, assets/ 등)를 전부 포함하는가.
2. **`js/config.js` ↔ `docker/config.docker.js` 동기화** — 두 파일의 top-level
   `XXX_CONFIG` 상수 집합이 일치하는가. (Phase 3에서 단일화 예정, 그 전까지는
   이 검사가 divergence 방지)
3. **`backend/requirements.txt` 변경 감지** — 수정됐다면 다음 배포 시 전체
   이미지 재빌드가 필요함을 경고 (패치 배포는 Python 의존성에 반영 안 됨).
4. **이중 Docker 데몬 감지** — WSL2 네이티브 `dockerd`가 Docker Desktop과
   병존하는지 검사 (2026-04-11 "유령 컨테이너" 사건 재발 방지).

## 종료 코드

- `0` — 모두 정상
- `1` — 경고 있음 (정보성, 빌드 차단 X)
- `2` — 오류 있음 (해결 필요, 빌드 차단 권장)

## 사용

```bash
python scripts/check-docker-parity.py            # 전체 검사
python scripts/check-docker-parity.py --quick    # 이중 데몬 검사 건너뜀
python scripts/check-docker-parity.py --json     # JSON 출력 (CI/훅 연계용)
```

Python 3.6+ (stdlib만 사용, 추가 의존성 없음)
"""

from __future__ import annotations

import fnmatch
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Set, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ── 프론트엔드 자산 판정 규칙 ──
# nginx 이미지가 서빙해야 할 리소스 식별 (휴리스틱)
FRONTEND_FILE_EXTS: Set[str] = {
    '.html', '.htm', '.svg', '.ico', '.png', '.jpg', '.jpeg', '.gif',
    '.webp', '.webmanifest', '.woff', '.woff2', '.ttf', '.eot', '.otf',
}
FRONTEND_SPECIAL_FILES: Set[str] = {
    'robots.txt', 'sitemap.xml', 'manifest.json', 'favicon.svg',
    'humans.txt', 'security.txt',
}
FRONTEND_DIRS: Set[str] = {
    'css', 'js', 'docs', 'fonts', 'assets', 'images', 'img',
    'static', 'public',
}


# ── 출력 색상 (TTY에서만) ──
def _color(s: str, code: str) -> str:
    if not sys.stdout.isatty() or os.environ.get('NO_COLOR'):
        return s
    return f'\033[{code}m{s}\033[0m'


def red(s: str) -> str: return _color(s, '31')
def yellow(s: str) -> str: return _color(s, '33')
def green(s: str) -> str: return _color(s, '32')
def cyan(s: str) -> str: return _color(s, '36')
def bold(s: str) -> str: return _color(s, '1')


# ── 결과 수집 ──
class CheckResult:
    def __init__(self) -> None:
        self.checks: List[dict] = []

    def add(self, check_name: str, level: str, summary: str, detail: str = '') -> None:
        """level ∈ {'ok', 'warn', 'error'}"""
        self.checks.append({
            'check': check_name,
            'level': level,
            'summary': summary,
            'detail': detail,
        })

    @property
    def ok_count(self) -> int:
        return sum(1 for c in self.checks if c['level'] == 'ok')

    @property
    def warn_count(self) -> int:
        return sum(1 for c in self.checks if c['level'] == 'warn')

    @property
    def error_count(self) -> int:
        return sum(1 for c in self.checks if c['level'] == 'error')

    def exit_code(self) -> int:
        if self.error_count > 0:
            return 2
        if self.warn_count > 0:
            return 1
        return 0


# ── Dockerfile COPY 패턴 추출 ──
_COPY_RE = re.compile(r'^\s*COPY\s+(?:--[\w=.:/-]+\s+)*(.+?)\s+(\S+)\s*$')


def parse_dockerfile_copy_patterns(dockerfile_path: Path) -> List[Tuple[str, str]]:
    """
    Dockerfile에서 COPY 라인을 파싱해 [(src, dst), ...] 리스트를 반환.
    단일 소스·다중 소스(COPY a b c dst) 모두 지원. 주석은 무시.
    """
    patterns: List[Tuple[str, str]] = []
    if not dockerfile_path.exists():
        return patterns

    with dockerfile_path.open(encoding='utf-8') as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue
            m = _COPY_RE.match(stripped)
            if not m:
                continue
            src_part = m.group(1)
            dst = m.group(2)
            # 다중 소스: 공백으로 분리
            for src in src_part.split():
                patterns.append((src, dst))
    return patterns


def _matches_copy_pattern(item: str, pattern: str) -> bool:
    """프로젝트 루트 아이템이 COPY 패턴에 걸리는지 확인."""
    # 정확 일치
    if pattern == item:
        return True
    # 디렉터리 끝 슬래시 정규화
    if pattern.rstrip('/') == item.rstrip('/'):
        return True
    # glob 패턴 (*.html 등)
    if fnmatch.fnmatch(item, pattern):
        return True
    # 경로 중첩 (docker/config.docker.js는 docker/ 안이라 item="docker/..."로 매칭됨)
    # 루트 아이템만 체크하므로 여기선 해당 없음
    return False


# ── 검사 1: 프론트엔드 자산 커버리지 ──
def check_frontend_coverage(result: CheckResult) -> None:
    name = "프론트엔드 자산 커버리지"
    dockerfile_nginx = PROJECT_ROOT / 'docker' / 'Dockerfile.nginx'
    if not dockerfile_nginx.exists():
        result.add(name, 'error', "docker/Dockerfile.nginx 없음")
        return

    patterns = parse_dockerfile_copy_patterns(dockerfile_nginx)
    # 루트 디렉터리 기준 패턴만 추출 (docker/..., etc/... 제외)
    root_patterns = [src for src, dst in patterns if '/' not in src.rstrip('/')]

    # 프로젝트 루트의 프론트엔드 후보 수집
    frontend_items: List[str] = []
    for entry in sorted(PROJECT_ROOT.iterdir()):
        name_ = entry.name
        if name_.startswith('.'):
            continue
        if entry.is_dir():
            if name_ in FRONTEND_DIRS:
                frontend_items.append(name_)
        else:
            ext = entry.suffix.lower()
            if ext in FRONTEND_FILE_EXTS or name_ in FRONTEND_SPECIAL_FILES:
                frontend_items.append(name_)

    missing: List[str] = []
    for item in frontend_items:
        covered = any(_matches_copy_pattern(item, p) for p in root_patterns)
        if not covered:
            missing.append(item)

    if missing:
        detail = (
            "다음 항목이 docker/Dockerfile.nginx의 COPY 패턴에 포함되지 않습니다.\n"
            "로컬에선 존재하지만 도커 이미지에는 빠집니다.\n\n"
            "    누락: " + ", ".join(missing) + "\n\n"
            "해결 방법:\n"
            "  1. 해당 파일/폴더를 도커에 포함해야 하면 docker/Dockerfile.nginx에\n"
            "     COPY 라인 추가 (예: COPY fonts/ /app/frontend/fonts/)\n"
            "  2. docker-compose.override.yml에도 bind mount 추가 (개발 동기화용)\n"
            "  3. 이 항목이 nginx와 무관하다면 이 스크립트의 FRONTEND_* 상수나\n"
            "     프로젝트 구조를 확인하세요."
        )
        result.add(name, 'warn', f"프론트엔드 자산 {len(missing)}건 누락", detail)
    else:
        result.add(
            name, 'ok',
            f"루트 프론트엔드 자산 {len(frontend_items)}건 전부 COPY 패턴으로 커버됨"
        )


# ── 검사 2: config.js ↔ config.docker.js 동기화 ──
_CONST_RE = re.compile(r'^\s*(?:const|let|var)\s+(\w+_CONFIG)\s*=', re.MULTILINE)


def check_config_sync(result: CheckResult) -> None:
    name = "config.js ↔ config.docker.js 동기화"
    js_config = PROJECT_ROOT / 'js' / 'config.js'
    docker_config = PROJECT_ROOT / 'docker' / 'config.docker.js'

    if not js_config.exists():
        result.add(name, 'error', "js/config.js 없음")
        return

    if not docker_config.exists():
        # Phase 3 완료 후 기대 상태
        result.add(
            name, 'ok',
            "docker/config.docker.js 없음 — Phase 3 단일화 이후 예상 상태"
        )
        return

    js_text = js_config.read_text(encoding='utf-8', errors='replace')
    docker_text = docker_config.read_text(encoding='utf-8', errors='replace')

    js_consts = set(_CONST_RE.findall(js_text))
    docker_consts = set(_CONST_RE.findall(docker_text))

    missing_in_docker = js_consts - docker_consts
    extra_in_docker = docker_consts - js_consts

    js_lines = len(js_text.splitlines())
    docker_lines = len(docker_text.splitlines())
    line_diff = abs(js_lines - docker_lines)

    issues: List[str] = []
    if missing_in_docker:
        issues.append(
            f"js/config.js에만 있는 상수 (docker 반영 필요): "
            + ", ".join(sorted(missing_in_docker))
        )
    if extra_in_docker:
        issues.append(
            f"docker/config.docker.js에만 있는 상수 (로컬 누락 의심): "
            + ", ".join(sorted(extra_in_docker))
        )
    if line_diff > 10:
        issues.append(
            f"라인 수 차이 큼 ({js_lines}줄 vs {docker_lines}줄, 차이 {line_diff}줄) "
            f"— 수동 동기화 누락 가능성"
        )

    if issues:
        detail = (
            "\n".join(f"  - {i}" for i in issues) + "\n\n"
            "해결 방법:\n"
            "  1. (단기) 두 파일을 수동으로 동기화 — backendUrl/ollamaUrl만\n"
            "     차이가 나야 합니다 (로컬=절대경로, 도커=상대경로).\n"
            "  2. (근본) Plan-31 Phase 3로 진행하여 이중화 제거.\n"
            "     `memory/reference_plan31.md` 참조."
        )
        result.add(
            name, 'warn',
            f"config divergence {len(issues)}건",
            detail
        )
    else:
        result.add(
            name, 'ok',
            f"config 상수 {len(js_consts)}개 일치 (라인차 {line_diff}줄 이내)"
        )


# ── 검사 3: backend/requirements.txt 변경 감지 ──
def check_requirements_freshness(result: CheckResult) -> None:
    name = "backend/requirements.txt 변경"
    req = PROJECT_ROOT / 'backend' / 'requirements.txt'
    if not req.exists():
        result.add(name, 'ok', "해당 없음 (파일 없음)")
        return

    try:
        proc = subprocess.run(
            ['git', 'status', '--short', 'backend/requirements.txt'],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        result.add(name, 'warn', f"git 상태 확인 실패: {e}")
        return

    if proc.returncode != 0:
        result.add(name, 'warn', f"git status 실패: {proc.stderr.strip()}")
        return

    if proc.stdout.strip():
        detail = (
            "backend/requirements.txt가 git HEAD 대비 수정됨.\n\n"
            "영향:\n"
            "  - Python 의존성은 Docker 이미지 레이어에 구워지므로\n"
            "    patch-apply.sh 코드 패치로는 반영되지 않습니다.\n"
            "  - 다음 배포 시 전체 이미지 재빌드가 필요합니다.\n\n"
            "해결:\n"
            "  - 개발 PC에서: `docker compose build backend`\n"
            "  - 배포: /docker-release (전체 이미지 tar)"
        )
        result.add(name, 'warn', "requirements.txt 수정됨 — 재빌드 필요", detail)
    else:
        result.add(name, 'ok', "git HEAD와 일치")


# ── 검사 4: 이중 Docker 데몬 감지 ──
def check_dual_docker_daemon(result: CheckResult) -> None:
    name = "이중 Docker 데몬"
    # Linux/WSL에서만 의미 있음
    if sys.platform not in ('linux', 'linux2'):
        result.add(name, 'ok', f"해당 없음 (platform={sys.platform})")
        return

    native_active = False
    try:
        proc = subprocess.run(
            ['systemctl', 'is-active', 'docker'],
            capture_output=True,
            text=True,
            timeout=3,
        )
        # is-active는 active면 rc=0, inactive면 rc=3, 없으면 rc!=0
        if 'active' in proc.stdout.strip() and 'inactive' not in proc.stdout.strip():
            native_active = True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        # systemctl 없음 = WSL 아닌 리눅스이거나 환경 이슈. 검사 생략.
        result.add(name, 'ok', "systemctl 접근 불가, 검사 생략")
        return

    is_docker_desktop = False
    try:
        proc = subprocess.run(
            ['docker', 'info', '--format', '{{.OperatingSystem}}'],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if 'Docker Desktop' in proc.stdout:
            is_docker_desktop = True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        result.add(name, 'warn', "docker info 접근 불가")
        return

    if native_active and is_docker_desktop:
        detail = (
            "WSL2 네이티브 dockerd가 Docker Desktop과 병존하고 있습니다.\n\n"
            "이것은 2026-04-11 'Plan-31 Phase 1' 유령 컨테이너 사건과\n"
            "동일한 위험입니다. 네이티브 dockerd의 옛 컨테이너가 port 80을\n"
            "선점하여 Docker Desktop의 새 컨테이너가 실제로 트래픽을 받지\n"
            "못할 수 있습니다.\n\n"
            "해결:\n"
            "  sudo systemctl stop docker docker.socket\n"
            "  sudo systemctl disable docker docker.socket\n\n"
            "또는 기존 유틸 스크립트:\n"
            "  sudo bash scripts/ghost-dockerd-disable.sh\n\n"
            "배경: memory/project_docker_dev_env.md"
        )
        result.add(name, 'error', "이중 데몬 병존 — 유령 dockerd 재발 가능", detail)
    elif native_active:
        result.add(
            name, 'warn',
            "네이티브 dockerd만 active (Docker Desktop 미감지)"
        )
    else:
        result.add(name, 'ok', "Docker Desktop 단일 데몬 (정상)")


# ── 출력 ──
def print_human(result: CheckResult) -> None:
    print(bold(cyan("== Docker Parity Check ==")))
    print(f"Project: {PROJECT_ROOT}")
    print()

    for i, check in enumerate(result.checks, 1):
        level = check['level']
        if level == 'ok':
            tag = green('OK  ')
        elif level == 'warn':
            tag = yellow('WARN')
        else:
            tag = red('ERR ')
        print(f"  [{i}] {tag} {bold(check['check'])}")
        print(f"         {check['summary']}")
        if check['detail'] and level != 'ok':
            for line in check['detail'].splitlines():
                print(f"         {line}")
        print()

    print(bold("=== 요약 ==="))
    print(
        f"  {green(f'OK={result.ok_count}')}  "
        f"{yellow(f'WARN={result.warn_count}')}  "
        f"{red(f'ERR={result.error_count}')}"
    )

    code = result.exit_code()
    if code == 0:
        print(green(bold("\n✓ 모두 정상. 빌드/배포 진행 가능.")))
    elif code == 1:
        print(yellow(bold("\n⚠ 경고 있음. 내용 검토 후 진행 결정.")))
    else:
        print(red(bold("\n✗ 오류 있음. 해결 후 다시 실행.")))


def print_json(result: CheckResult) -> None:
    out = {
        'exit_code': result.exit_code(),
        'summary': {
            'ok': result.ok_count,
            'warn': result.warn_count,
            'error': result.error_count,
        },
        'checks': result.checks,
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))


# ── 메인 ──
def main() -> int:
    args = sys.argv[1:]
    quick = '--quick' in args
    as_json = '--json' in args

    result = CheckResult()

    check_frontend_coverage(result)
    check_config_sync(result)
    check_requirements_freshness(result)
    if not quick:
        check_dual_docker_daemon(result)

    if as_json:
        print_json(result)
    else:
        print_human(result)

    return result.exit_code()


if __name__ == '__main__':
    sys.exit(main())
