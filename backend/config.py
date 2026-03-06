"""
백엔드 설정
"""
from pathlib import Path

# Ollama 서버 설정
OLLAMA_URL = "http://localhost:11434"  # 회사: http://<linux-server-ip>:11434
OLLAMA_MODEL = "gemma3:4b"

# 임베딩 설정
EMBEDDING_MODEL = "bge-m3"  # Ollama 임베딩 모델
EMBEDDING_DIMENSION = 1024  # bge-m3 출력 차원

# 검색 설정
SEARCH_INDEX_PATH = "../data/search-index.json"
VECTOR_INDEX_PATH = "../data/vector-index"  # .faiss + _meta.json
MAX_SEARCH_RESULTS = 5
MAX_CONTEXT_LENGTH = 8000
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
MAX_HISTORY_LENGTH = 2000        # 대화 기록 최대 문자 수 (8000자 중)
MAX_SESSIONS = 100               # 동시 세션 수 상한
MAX_IDLE_MINUTES = 60            # 유휴 세션 자동 삭제 시간(분)
QUERY_REWRITE_ENABLED = True     # 쿼리 재작성 활성화 여부

# 인증 설정
AUTH_DB_PATH = str(Path(__file__).parent.parent / "data" / "auth.db")
ANALYTICS_DB_PATH = str(Path(__file__).parent.parent / "data" / "analytics.db")
SESSION_EXPIRY_HOURS = 24
LOGIN_REQUIRED = True  # False: 열람 자유 (시범 운영용)
CORS_ORIGINS = ["http://localhost:8080", "http://127.0.0.1:8080"]

# 업로드 임시 디렉토리 (DRM 등으로 로컬 저장이 문제될 경우 네트워크 경로로 변경)
# 예: UPLOAD_TEMP_DIR = "\\\\server\\share\\webbook_temp"
UPLOAD_TEMP_DIR = None  # None이면 기본값 (backend/temp/)

# Word COM 전처리 (장절번호 평문화 + 필드 갱신)
# DRM 환경에서 COM 임시 파일이 암호화되어 변환 실패 시 False로 설정
WORD_COM_PREPROCESS = False

# Translator 설정
TRANSLATOR_DATA_DIR = str(Path(__file__).parent.parent / "data" / "translator")
TRANSLATOR_MAX_PDF_SIZE = 100 * 1024 * 1024  # 100MB
TRANSLATOR_TRANSLATION_MODEL = ""  # 빈값이면 OLLAMA_MODEL 폴백
TRANSLATOR_PMT_TIMEOUT = 3600  # 60분, 레거시 통번역 타임아웃
TRANSLATOR_PAGE_TIMEOUT = 300  # 5분, 페이지별 번역 타임아웃
TRANSLATOR_MAX_CONCURRENT = 4  # 동시 번역 최대 수 (GPU 부하 제한)
TRANSLATOR_CUSTOM_PROMPT = ""          # --custom-system-prompt
TRANSLATOR_DISABLE_RICH_TEXT = False    # --disable-rich-text-translate
TRANSLATOR_TRANSLATE_TABLE = False      # --translate-table-text
TRANSLATOR_MIN_TEXT_LENGTH = 0          # --min-text-length
TRANSLATOR_QPS = 0                      # --qps (0=무제한)
TRANSLATOR_OCR_WORKAROUND = False       # --ocr-workaround
TRANSLATOR_ENHANCE_COMPAT = False       # --enhance-compatibility

# Translator 텍스트 번역 (폴백 엔진)
TRANSLATOR_TEXT_FONT_SCALE = 0.75       # EN→KR 기본 폰트 축소 비율
TRANSLATOR_TEXT_MIN_SCALE = 0.5         # insert_htmlbox scale_low (최소 축소 한도)
TRANSLATOR_TEXT_FONT_FAMILY = "sans-serif"  # 번역 폰트 패밀리
TRANSLATOR_TEXT_MIN_TEXT_LENGTH = 0         # 최소 텍스트 길이 (미만 건너뜀)
TRANSLATOR_TEXT_CUSTOM_PROMPT = (
    "You are a professional Korean native translator who needs to "
    "fluently translate text into Korean.\n\n"
    "## Rules\n"
    "1. Translate ALL human-readable content into Korean.\n"
    "2. If the entire input is pure code/identifiers, return it unchanged.\n"
    "3. Preserve list markers (bullets, numbering) in their original format.\n"
    "4. If you see '---' separators, keep them in the output.\n\n"
    "## Output\n"
    "Output ONLY the translated Korean text. No explanations, no extra text."
)

# 서버 설정
HOST = "0.0.0.0"
PORT = 8000
