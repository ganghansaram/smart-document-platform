"""
백엔드 설정

환경변수로 오버라이드 가능한 설정:
    OLLAMA_URL          Ollama 서버 주소 (기본: http://localhost:11434)
    CORS_ORIGINS        CORS 허용 오리진 (쉼표 구분, 기본: http://localhost:8080)
"""
import os
from pathlib import Path

# Ollama 서버 설정
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:4b")

# LLM 프로바이더 설정
LLM_PROVIDER = "ollama"           # "ollama" | "openai_compat"
LLM_ENDPOINT = ""                 # OpenAI-compat 엔드포인트 URL (예: https://model-server/v1)
LLM_API_KEY = ""                  # API 키 (필요 시)
LLM_MODEL_ID = ""                 # 엔드포인트의 모델 ID

# 임베딩 설정
# Plan-40: 용도별 백엔드 분리 — INDEX(대량 인덱싱)와 RUNTIME(실시간 검색·유사도)을 독립 선택 가능.
# 미설정 시 EMBEDDING_BACKEND(레거시 전역)로 폴백 → 코드 기본값 순서로 해석.
EMBEDDING_BACKEND = os.getenv("EMBEDDING_BACKEND", "")  # 레거시 전역 토글 (deprecated, 하위호환용)
EMBEDDING_BACKEND_INDEX = os.getenv("EMBEDDING_BACKEND_INDEX", "")    # 인덱싱 경로 (기본: ollama — GPU 가속)
EMBEDDING_BACKEND_RUNTIME = os.getenv("EMBEDDING_BACKEND_RUNTIME", "")  # 런타임 경로 (기본: local — 저지연)
EMBEDDING_LOCAL_MODEL = str(Path(__file__).parent.parent / "models" / "bge-m3")
EMBEDDING_MODEL = "bge-m3"  # Ollama 임베딩 모델 (ollama 백엔드 시 사용)
EMBEDDING_DIMENSION = 1024  # bge-m3 출력 차원
EMBEDDING_BATCH_SIZE = 64   # 로컬 추론 배치 크기
EMBEDDING_OLLAMA_BATCH = int(os.getenv("EMBEDDING_OLLAMA_BATCH", "256"))  # Ollama HTTP 경로 청크 분할 크기 (0=분할 비활성). Phase 0 실측: 500까지 안정, 200~500 throughput 최대. 256은 안전 마진 포함 기본값.

# 검색 설정
SEARCH_INDEX_PATH = "../data/search-index.json"
VECTOR_INDEX_PATH = "../data/vector-index"  # .faiss + _meta.json
MAX_SEARCH_RESULTS = 5       # 27b 권장: 7 (더 많은 문서 참조)
MAX_CONTEXT_LENGTH = 8000    # 27b 권장: 16000 (128K 컨텍스트 활용)
DEFAULT_SEARCH_TYPE = "hybrid"  # "keyword" | "vector" | "hybrid"
HYBRID_KEYWORD_WEIGHT = 0.3  # 키워드 점수 비중 (1 - 이 값 = 벡터 비중)
HYBRID_RRF_K = 60  # RRF 상수 (높을수록 순위 차이 완화)
MIN_VECTOR_SCORE = 0.48  # 벡터 검색 최소 유사도 (이하 결과 제거)

# 리랭커 설정
RERANKER_ENABLED = True  # False면 리랭킹 스킵
RERANKER_MODEL = str(Path(__file__).parent.parent / "models" / "bge-reranker-v2-m3")
RERANKER_TOP_K_MULTIPLIER = 3  # 리랭킹 전 후1보 수 = top_k * 이 값

# 멀티턴 대화 설정
MAX_CONVERSATION_TURNS = 5       # 프롬프트에 포함할 최대 대화 턴 수
MAX_HISTORY_LENGTH = 2000        # 대화 기록 최대 문자 수, 27b 권장: 4000
MAX_SESSIONS = 100               # 동시 세션 수 상한
MAX_IDLE_MINUTES = 60            # 유휴 세션 자동 삭제 시간(분)
QUERY_REWRITE_ENABLED = True     # 쿼리 재작성 활성화 여부
QUERY_DECOMPOSE_ENABLED = True   # 쿼리 분해 활성화 여부 (복합 질문 → 서브쿼리)
QUESTION_ROUTING_ENABLED = True  # 질문 유형 분류 (SIMPLE/COMPARE/REASON/CHAT)
MAX_AGENT_ITERATIONS = 3         # Agentic RAG 최대 반복 횟수

# 챗봇 시스템 프롬프트 (빈값이면 llm_client.py의 기본 프롬프트 사용)
CHAT_SYSTEM_PROMPT = ""

# 인증 설정
AUTH_DB_PATH = str(Path(__file__).parent.parent / "data" / "auth.db")
ANALYTICS_DB_PATH = str(Path(__file__).parent.parent / "data" / "analytics.db")
SESSION_EXPIRY_HOURS = 24
LOGIN_REQUIRED = True  # False: 열람 자유 (시범 운영용)
CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS", "http://localhost:8080,http://127.0.0.1:8080"
).split(",")

# 업로드 임시 디렉토리 (DRM 등으로 로컬 저장이 문제될 경우 네트워크 경로로 변경)
# 예: UPLOAD_TEMP_DIR = "\\\\server\\share\\webbook_temp"
UPLOAD_TEMP_DIR = None  # None이면 기본값 (backend/temp/)

# Word COM 전처리 (장절번호 평문화 + 필드 갱신)
# DRM 환경에서 COM 임시 파일이 암호화되어 변환 실패 시 False로 설정
WORD_COM_PREPROCESS = False

# Verify 설정
VERIFY_DATA_DIR = str(Path(__file__).parent.parent / "data" / "verify")
VERIFY_HISTORY_MAX = 10

# Translator 설정
TRANSLATOR_DATA_DIR = str(Path(__file__).parent.parent / "data" / "translator")
TRANSLATOR_MAX_PDF_SIZE = 100 * 1024 * 1024  # 100MB
TRANSLATOR_MODEL = ""  # Notebook 전용 모델 (번역+요약 공용). 빈값이면 OLLAMA_MODEL 폴백
TRANSLATOR_PMT_TIMEOUT = 3600  # 60분, 레거시 통번역 타임아웃
TRANSLATOR_PAGE_TIMEOUT = 300  # 5분, 페이지별 번역 타임아웃
TRANSLATOR_MAX_CONCURRENT = 4  # 동시 번역 최대 수 (GPU 부하 제한)

# Plan-44 Phase 2b: LLM Gateway (동시성 상한 + 스트림 전용 슬롯)
# 기본값 False = shadow 단계 (Gateway 경유하되 Semaphore 우회, Phase 2a 와 동일 동작)
# True 로 전환 시 Gateway Semaphore 활성화
LLM_GATEWAY_ENABLED = False
LLM_GATEWAY_MAX_CONCURRENT = 8    # 단발 호출(chat/summary/classify/rewrite) 동시 상한
LLM_GATEWAY_MAX_QUEUE = 32        # 대기열 한도 (초과 시 429)
LLM_GATEWAY_STREAM_SLOTS = 3      # 스트림 전용 슬롯 (qa_stream), 긴 스트림이 단발 굶주림 유발 방지
TRANSLATOR_CUSTOM_PROMPT = ""          # --custom-system-prompt
TRANSLATOR_DISABLE_RICH_TEXT = False    # --disable-rich-text-translate
TRANSLATOR_TRANSLATE_TABLE = False      # --translate-table-text
TRANSLATOR_MIN_TEXT_LENGTH = 0          # --min-text-length
TRANSLATOR_QPS = 0                      # --qps (0=무제한)
TRANSLATOR_OCR_WORKAROUND = False       # --ocr-workaround
TRANSLATOR_ENHANCE_COMPAT = False       # --enhance-compatibility

# Translator AI 선택 번역/요약
TRANSLATOR_AI_SELECTION_TIMEOUT = 30       # 초
TRANSLATOR_AI_TRANSLATE_PROMPT = (
    "다음 텍스트를 한국어로 자연스럽게 번역하세요. "
    "원문의 기술 용어는 괄호 안에 영문을 병기하세요. "
    "번역문만 출력하세요."
)
TRANSLATOR_AI_SUMMARIZE_PROMPT = (
    "다음 텍스트를 한국어로 3문장 이내로 요약하세요. "
    "핵심 논점만 간결하게 전달하세요. "
    "요약문만 출력하세요."
)

# Translator 웹 뷰 (Markdown 추출/번역)
TRANSLATOR_WEB_TABLE_MODE = "image"            # "extract" | "image" | "off"
TRANSLATOR_WEB_FORMULA_MODE = "image"          # "latex" | "image" | "off"
TRANSLATOR_WEB_IMAGE_DPI = 150                 # 추출 이미지 해상도 (72~300)
TRANSLATOR_WEB_AUTO_SUMMARY = False            # 번역 완료 시 자동 요약 생성
TRANSLATOR_WEB_TABLE_STRATEGY = "lines_strict" # PyMuPDF 표 감지 전략
TRANSLATOR_WEB_DEBUG = False                   # 디버그: 추출 중간 결과 파일 저장

# Translator AI 요약·Q&A
# 요약 모델: TRANSLATOR_MODEL 공용 (Plan-32에서 TRANSLATOR_AI_SUMMARY_MODEL 통합)
TRANSLATOR_AI_SUMMARY_THRESHOLD = 0            # 0 = 기본값(12000자), >0 = 수동 지정. 이하 → 단일패스, 초과 → 계층적
TRANSLATOR_AI_QA_THRESHOLD = 0                 # 0 = 기본값(12000자), >0 = 수동 지정. 이하 → 직접주입, 초과 → 섹션선별

# Compare AI 의미 분류 설정
COMPARE_AI_ENABLED = True
COMPARE_AI_MODEL = ""           # 빈값이면 OLLAMA_MODEL 폴백
COMPARE_AI_TEMPERATURE = 0      # 분류 일관성 최대화
COMPARE_AI_BATCH_SIZE = 20      # 1회 LLM 호출당 최대 변경 구간 수
COMPARE_AI_TIMEOUT = 60         # LLM 호출 타임아웃(초)
COMPARE_AI_SYSTEM_PROMPT = ""   # 빈값이면 기본 내장 프롬프트 사용

# ── Verify: 유사도 검사 (Plan-38 Phase 1 외부화) ──
VERIFY_SIMILARITY_THRESHOLD_HIGH = 0.85    # 의미 유사 high (paraphrase·translation·near_copy 판정 기준)
VERIFY_SIMILARITY_THRESHOLD_MEDIUM = 0.75  # 의미 유사 medium (near_copy 약화 판정)
VERIFY_SIMILARITY_WINNOW_K = 25            # Winnowing k-gram 크기
VERIFY_SIMILARITY_WINNOW_WINDOW = 4        # Winnowing sliding window
VERIFY_SIMILARITY_EMBEDDING_BATCH = 64     # 임베딩 배치 크기

# 분류 임계값 (Phase 1.1 신규 — 하드코딩 제거)
VERIFY_SIMILARITY_PARA_FP_MAX = 0.40       # paraphrase 어휘 fingerprint 상한
VERIFY_SIMILARITY_TRANS_FP_MAX = 0.10      # translation 어휘 fingerprint 상한 (다른 언어)
# Cross-language(다른 스크립트) 의미 임계값 — bge-m3 cross-lingual 점수 분포 반영 (R1 캘리브레이션)
# Korean-English 정상 번역도 sem 0.65~0.75 구간에 분포 (monolingual 0.85+ 대비 낮음)
VERIFY_SIMILARITY_CROSS_LANG_SEM_TH = 0.65  # translation 분류용 별도 임계값

# 짧은 매칭 필터 (Phase 1.3 신규)
VERIFY_SIMILARITY_MIN_MATCH_WORDS = 8      # 매칭 대상 문장 최소 단어 수

# 정형 구문 검출 임계값 (R1 캘리브레이션 — boilerplate-heavy 변형이 paraphrase로 새는 현상 해소)
# 문장의 N% 이상이 정형 구문 phrase로 구성되면 boilerplate 판정
VERIFY_SIMILARITY_BOILERPLATE_TH = 0.40    # 0.50 → 0.40 (보수적 → 균형)

# 5단계 신호등 경계 (Phase 2 — Plan §7.1)
# 기존 LOW/HIGH 2단계는 호환 유지, 신규 5단계 추가
VERIFY_SIMILARITY_VERDICT_LOW = 30         # [호환] 양호/보통 경계 (%)
VERIFY_SIMILARITY_VERDICT_HIGH = 60        # [호환] 보통/주의 경계 (%)
VERIFY_SIMILARITY_VERDICT_BANDS = [0, 25, 50, 75]  # Blue/Green/Yellow/Orange/Red 경계 (%)

# 검사 설정 기본값 — 사용자 토글 5옵션 (Phase 1.4)
# True면 점수 계산에서 제외, False면 포함. 프론트가 옵션으로 오버라이드 가능.
VERIFY_SIMILARITY_DEFAULTS = {
    "exclude_boilerplate": True,    # 정형구문
    "exclude_short_match": True,    # 짧은 매칭 (8단어 미만)
    "exclude_toc": True,            # 목차/장절 헤딩
    "exclude_caption": True,        # 표/그림 캡션
    "exclude_cited_quote": False,   # 인용·출처 표시 (사용자 선택)
}
# 백엔드 자동 처리 (사용자 토글 없음, 항상 ON):
#   - references_section: 참고문헌 섹션 이후
#   - spec_number_only: 규격 번호만 매칭 + 매우 짧음

# 서버 설정
HOST = "0.0.0.0"
PORT = 8000
