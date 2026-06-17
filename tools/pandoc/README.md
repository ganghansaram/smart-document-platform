# Pandoc 정적 바이너리 (Plan-60 통일 양식 DOCX 내보내기)

`docx_export_service.py` 가 `MD→HTML→DOCX` 변환에 사용하는 Pandoc 바이너리를 둔다.

## ⚠️ 바이너리는 git 에 커밋하지 않는다
용량(리눅스 ≈ 155MB)이 커 `.gitignore` 로 제외(`tools/pandoc/pandoc-*`).
**폐쇄망 배포 tar 에는 반드시 포함**해야 한다(런타임 다운로드 불가).

## 파일 규약 (플랫폼별)
| 플랫폼 | 파일명 | 용도 |
|--------|--------|------|
| Linux (Docker/회사 VM) | `pandoc-linux-amd64` | 백엔드 컨테이너 (debian) |
| Windows (회사 톰캣 PC) | `pandoc-windows-amd64.exe` | `python main.py` 직접 실행 |

`docx_export_service.resolve_pandoc()` 이 플랫폼에 맞는 파일을 자동 선택하고,
없으면 시스템 PATH 의 `pandoc` 로 폴백한다. `config.PANDOC_BIN` 으로 명시 지정도 가능.

## 조달 방법 (인터넷 가능 PC에서 1회)
```bash
# Linux (현재 버전: 3.10)
curl -sL -o pandoc.tar.gz \
  https://github.com/jgm/pandoc/releases/download/3.10/pandoc-3.10-linux-amd64.tar.gz
tar xzf pandoc.tar.gz --strip-components=2 -C . pandoc-3.10/bin/pandoc
mv pandoc pandoc-linux-amd64 && chmod +x pandoc-linux-amd64 && rm pandoc.tar.gz

# Windows (회사 톰캣 배포용 — 별도 PC에서 받아 동봉)
#   https://github.com/jgm/pandoc/releases/download/3.10/pandoc-3.10-windows-x86_64.zip
#   압축 해제 후 pandoc.exe → pandoc-windows-amd64.exe 로 이름 변경하여 이 폴더에 배치
```

## Docker 빌드
`Dockerfile` 의 `COPY tools/ /app/tools/` 로 이 폴더가 이미지에 자동 포함된다
(별도 Dockerfile 수정 불필요). 바이너리가 빌드 머신에 존재해야 함.

## GPL 주의
Pandoc 은 GPL. **별도 실행파일을 subprocess 로 호출**하므로 본 프로젝트 코드에는
GPL 이 전염되지 않는다(정적/동적 링크 아님).
