# Plan-60 Phase 3a — 내보내기 엔진 구현 + 검증 피드백

> 작성 2026-06-16 · 범위: pandoc 동봉 + `/api/export-docx` 코어 (MD→HTML→DOCX + 표지 주입)
> 관점: 개발책임자(영향성·배포) + 코드전문가(정확성·보안·회귀)

## 1. 구현 요약

| 산출물 | 내용 |
|--------|------|
| `backend/services/docx_export_service.py` | 2단계 변환 파이프라인 + 표지 후처리 주입 + 리소스 해석 |
| `backend/api/export_docx.py` | `POST /api/export-docx` (require_editor, DOCX 다운로드) |
| `backend/assets/reference.docx` | 기본 통일 양식 템플릿 (이미지 동봉 fallback) |
| `tools/pandoc/pandoc-linux-amd64` | Pandoc 3.10 정적 바이너리 (gitignore, 배포 tar 동봉) |
| `tools/pandoc/README.md` | 바이너리 조달·배포 가이드 |
| `backend/config.py` | `PANDOC_BIN`·`EXPORT_REFERENCE_DOCX`·`EXPORT_TIMEOUT` |
| `backend/main.py` | 라우터 등록 1줄 |

**리소스 해석 (3단 폴백)**: pandoc = config → `tools/pandoc/<플랫폼>` → PATH · reference = config → `data/reference.docx`(관리자 교체) → `backend/assets/`(기본). → 회사 양식은 **`data/reference.docx` 파일 1개 교체**로 적용(코드 변경 0, 사양 일치).

## 2. ⚠️ 기존 기능 영향성 (가장 중요)

- **충돌 회피**: 기존 `export_service.py`(Verify/Compare **Excel(.xlsx)** 내보내기, route `POST /api/compare/export`)와 **이름·라우트 모두 분리**. 신규는 `docx_export_service.py` + `POST /api/export-docx`.
  - Write 도구 안전장치가 동명 파일 덮어쓰기를 차단 → 기존 Excel 기능 보존됨(만약 덮어썼다면 Verify 내보내기 전체 파괴될 뻔).
- **회귀 검사 통과**: 두 서비스 공존 임포트 OK · `/api/compare/export`·`/api/search` 정상 잔존 · 백엔드 클린 스타트(임포트 에러 0).
- **순수 추가(additive)**: 기존 파일 수정은 `main.py`(라우터 1줄)·`config.py`(설정 3개)·`.gitignore` 뿐. 기존 엔드포인트/서비스 로직 무수정.

## 3. 직접 테스트 검증 결과

### Test 1 — 서비스 정확성 (docx XML 측정 + 시각 렌더)
| 항목 | 결과 |
|------|------|
| pandoc/reference 자동 해석 | ✅ 번들 바이너리 + assets 기본 템플릿 |
| front matter 6필드 파싱(문서번호·보안등급 포함) | ✅ |
| 수식 oMath | ✅ 4 |
| 표 (단순 + 병합) | ✅ w:tbl 2, gridSpan 2 / vMerge 2 (병합 보존) |
| 표지 주입(대외비·문서번호) + 페이지나누기 | ✅ |
| 헤딩 자동번호 | ✅ |
| **시각 렌더(LibreOffice→PDF)** | ✅ 표지 page1 + 본문 page2, 병합표·단순표·양식 정상 |

### Test 2 — HTTP 엔드포인트 (인증·RBAC·다운로드)
| 케이스 | 결과 |
|--------|------|
| 미인증 호출 | ✅ 401 |
| 로그인(testbot) → 세션 쿠키 | ✅ |
| 인증 내보내기 | ✅ 200, DOCX content-type, PK 매직바이트, 표지 unzip 검증 |
| 한국어 파일명 | ✅ RFC 5987 `filename*` + ASCII 폴백 `document.docx` |
| 빈 md | ✅ 400 |

### 검증 중 발견·수정한 버그
- **파일명 ASCII 폴백 결함**: 비-ASCII 전용 파일명일 때 폴백이 `.docx` 만 남음 → stem 추출로 `document.docx` 폴백되도록 수정·재검증 완료.

## 4. 알려진 한계 · 후속 과제 (정직한 기록)

| # | 항목 | 영향 | 권고 |
|---|------|------|------|
| H1 | **수식 Word 렌더 미확정** | LibreOffice 빈칸(XML엔 정상) | 회사 Windows Word 로 1건 교차확인 (Phase 1 §8-E 이월) |
| H2 | **SSRF/원격 이미지** | pandoc html→docx 가 `<img src=http..>` 페치 가능 | 네트워크 노출 전 `--sandbox` 호환 검토 또는 원격 src 차단. 폐쇄망은 무망이라 저위험 |
| H3 | **입력 크기 제한 없음** | 초대형 md = 변환 부하 | max 길이 가드 추가(Phase 3 폴리시) |
| H4 | **Windows pandoc 미배치** | 회사 톰캣 배포 시 필요 | `pandoc-windows-amd64.exe` 동봉(README 참조) |
| H5 | **표지 머리글/바닥글 노출** | 표지에도 "기술 보고서"/페이지번호 | first-page 섹션 분리(Phase 3 폴리시) |
| H6 | **이미지 resource_path 미노출** | API 가 이미지 경로 안 받음 | Phase 2 저장 문서 연동 시 안전한 경로 해석 추가 |
| H7 | **프로덕션 이미지 미재빌드** | dev 컨테이너는 bind-mount 로 live, 배포본은 미반영 | 다음 릴리스 빌드 시 tools/pandoc 포함 확인 |

## 5. 배포 메모 (개발책임자)

- **Docker**: `Dockerfile` 의 `COPY tools/`·`COPY backend/` 가 pandoc 바이너리와 assets 를 이미지에 자동 포함 → **Dockerfile 수정 불필요**. 단 빌드 머신에 바이너리 존재 필수(gitignore 라 fresh clone 시 README 대로 조달).
- **회사 Windows(톰캣)**: `python main.py` 직접 실행 + `pandoc-windows-amd64.exe` 동봉 시 동작.
- **GPL**: pandoc 은 subprocess 호출(별도 실행파일) → 코드 전염 없음.

## 6. 다음 단계

1. **3b** — (이미 엔진에 포함) 표지 주입 완료. 표지 헤더 억제(H5)는 폴리시 단계로.
2. **3c** — 내보내기 버튼 UI (문서 필요 → Phase 2 이후).
3. **Phase 2** — 저작 경로(편집기·저장·소유권). 저장된 `.md` 를 `/api/export-docx` 가 소비.
4. **하드닝** — H2(SSRF)·H3(크기제한) 는 네트워크 노출/외부 사용 전 처리.
