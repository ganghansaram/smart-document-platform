# Smart Document Platform

## 핵심 제약
- **Vanilla JS only** — 프레임워크/라이브러리 금지 (폐쇄망 운용 환경)
- **모놀리식 HTML** — 각 서브시스템은 단일 HTML 파일 (inline JS/CSS)
- **빌드 시스템 없음** — 번들러, 트랜스파일러 사용하지 않음

## 실행 환경
```bash
# 백엔드 (FastAPI)
cd backend && python main.py          # http://localhost:8000

# 프론트엔드 (정적 서버)
python -m http.server 8080            # http://localhost:8080
```

## 서브시스템
| 시스템 | 진입점 | 설명 |
|--------|--------|------|
| 플랫폼 | `launcher.html`, `login.html` | 런처, 인증, 공통 헤더 |
| Explorer | `index.html` | 웹북 탐색기, RAG 검색, AI 채팅 |
| Translator | `translator.html` | 논문 번역, PDF 듀얼 뷰어 |
| Compare | (예정) | 문서 비교 |

## 작업 원칙
1. **의견 먼저, 구현은 승인 후** — 비자명한 작업은 먼저 논의
2. **기존 코드 읽고 나서 수정** — 패턴/컨벤션 파악 후 작업
3. **과도한 엔지니어링 금지** — 요청된 범위만 구현
4. **커밋은 요청 시에만** — 자동 커밋 금지, 규칙은 `.claude/skills/commit` 참조

## 테스트 계정
- ID: `testbot` / PW: `test1234`
