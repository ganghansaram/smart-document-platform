"""
Phase 6-0: AI 의미 분류 프롬프트 프로토타이핑 (v2 — NUMERIC 폐지)
================================================================
SWA_PMS 실문서 기반 샘플 diff 데이터로 Ollama 구조화 출력 테스트.
측정 항목: 분류 정확도, JSON 파싱 성공률, 응답 시간.

v2 변경:
- NUMERIC 태그 폐지 → 6종 태그 체계
- 수치 변경은 STRICTER/MORE_LENIENT로 흡수 (의무/허용 기준)
- 시스템 프롬프트에 '의무 vs 허용' 판단 기준 추가
- few-shot 예시에 수치 변경 사례 추가
"""

import json
import time
import httpx

OLLAMA_URL = "http://localhost:11434"

# ── 1. 샘플 diff 데이터 (SWA_PMS 기반 현실적 변경) ──

SAMPLE_CHANGES = [
    {
        "index": 0,
        "type": "modified",
        "text_a": "현재 여러 사업에서 동일한 표준 부품(예: 볼트, 너트, 패스너, 와셔 등)이 사용되고 있음에도 불구하고, 각 PLM 시스템에서 중복 등록되어 관리되고 있습니다.",
        "text_b": "현재 여러 사업에서 동일한 표준 부품(예: 볼트, 너트, 패스너, 와셔 등)이 사용되고 있음에도 불구하고, 각 PLM(Product Lifecycle Management) 시스템에서 중복 등록되어 관리되고 있습니다.",
        "expected_tag": "CLARIFICATION"
    },
    {
        "index": 1,
        "type": "modified",
        "text_a": "데이터 검증 자동화가 포함되며, 이를 통해 작업의 효율성을 높이고 데이터 신뢰성을 확보할 수 있습니다.",
        "text_b": "데이터 검증 자동화가 포함되며, 이를 통해 작업의 효율성을 높이고 데이터 신뢰성을 확보할 수 있습니다. 또한 외부 시스템과의 인터페이스 표준화를 통해 데이터 연계 범위를 확대합니다.",
        "expected_tag": "EXPANDED"
    },
    {
        "index": 2,
        "type": "modified",
        "text_a": "시스템의 응답 시간은 3초 이내로 유지해야 합니다.",
        "text_b": "시스템의 응답 시간은 1초 이내로 유지해야 합니다.",
        "expected_tag": "STRICTER"
    },
    {
        "index": 3,
        "type": "modified",
        "text_a": "데이터 백업은 매일 수행되어야 합니다.",
        "text_b": "데이터 백업은 매주 수행되어야 합니다.",
        "expected_tag": "MORE_LENIENT"
    },
    {
        "index": 4,
        "type": "modified",
        "text_a": "시스템은 동시 접속 사용자 50명을 지원해야 합니다.",
        "text_b": "시스템은 동시 접속 사용자 100명을 지원해야 합니다.",
        "expected_tag": "STRICTER"
    },
    {
        "index": 5,
        "type": "modified",
        "text_a": "이를 해결하기 위해 표준 부품의 상위 정보를 관리하는 PPSL 항목이 도입되었지만",
        "text_b": "이 문제를 해결하기 위해 표준 부품의 상위 정보를 관리하는 PPSL 항목이 도입되었으나",
        "expected_tag": "EDITORIAL"
    },
    {
        "index": 6,
        "type": "modified",
        "text_a": "2.3 Design Decisions\n시스템 아키텍처는 마이크로서비스 기반으로 설계한다.",
        "text_b": "2.4 Design Decisions\n시스템 아키텍처는 마이크로서비스 기반으로 설계한다.",
        "expected_tag": "RESTRUCTURED"
    },
    {
        "index": 7,
        "type": "added",
        "text_a": None,
        "text_b": "3.5 보안 요구사항\n모든 API 통신은 TLS 1.3 이상을 사용해야 하며, 인증 토큰의 유효기간은 30분으로 제한한다.",
        "expected_tag": "EXPANDED"
    },
    {
        "index": 8,
        "type": "deleted",
        "text_a": "참고: 본 문서는 초안이며 최종 승인 전까지 변경될 수 있습니다.",
        "text_b": None,
        "expected_tag": "EDITORIAL"
    },
    {
        "index": 9,
        "type": "modified",
        "text_a": "사용자 인증은 LDAP 연동을 통해 구현한다.",
        "text_b": "사용자 인증은 LDAP 연동을 통해 구현하며, 2단계 인증(MFA)을 필수 적용한다.",
        "expected_tag": "STRICTER"
    },
    {
        "index": 10,
        "type": "modified",
        "text_a": "테스트 커버리지는 80% 이상을 유지해야 한다.",
        "text_b": "테스트 커버리지는 70% 이상을 유지해야 한다.",
        "expected_tag": "MORE_LENIENT"
    },
    {
        "index": 11,
        "type": "modified",
        "text_a": "최대 파일 업로드 크기는 10MB이다.",
        "text_b": "최대 파일 업로드 크기는 50MB이다.",
        "expected_tag": "MORE_LENIENT"
    },
    {
        "index": 12,
        "type": "modified",
        "text_a": "설계자는 부품 정보를 검색하거나 신규 부품 등록을 요청하며, 분석가는 데이터를 통해 품질 및 설계 관련 리포트를 생성합니다.",
        "text_b": "설계자는 부품 정보를 검색하거나 신규 부품 등록을 요청하고, 분석가는 데이터를 활용하여 품질 및 설계 관련 리포트를 생성합니다.",
        "expected_tag": "EDITORIAL"
    },
    {
        "index": 13,
        "type": "modified",
        "text_a": "3.2 Deployment View\n시스템은 온프레미스 환경에 배포된다.",
        "text_b": "3.2 Deployment View\n시스템은 온프레미스 또는 클라우드 하이브리드 환경에 배포될 수 있다.",
        "expected_tag": "MORE_LENIENT"
    },
    {
        "index": 14,
        "type": "modified",
        "text_a": "데이터 보관 기간은 5년이다.",
        "text_b": "데이터 보관 기간은 10년이다.",
        "expected_tag": "STRICTER"
    },
]


# ── 2. 시스템 프롬프트 ──

SYSTEM_PROMPT = """당신은 기술문서 변경사항을 분류하는 전문가입니다.
두 문서 버전 간의 변경 구간을 받아, 각 변경의 의미적 유형을 분류합니다.

## 분류 태그 (정확히 6종 중 하나를 선택)

- EDITORIAL: 편집상 변경. 오타 수정, 표현 다듬기, 접속사/어미 변경 등. 의미에 영향 없음.
- CLARIFICATION: 기존 내용의 표현을 명확하게 보완. 약어 풀네임 병기, 용어 설명 추가 등. 의미 자체는 동일.
- STRICTER: 요구사항/기준/제약이 더 엄격해짐. 시스템이 달성해야 할 의무가 강화된 경우.
- MORE_LENIENT: 요구사항/기준/제약이 완화됨. 사용자에게 허용된 범위가 넓어지거나 의무가 줄어든 경우.
- EXPANDED: 기존에 없던 새 내용/범위/기능 추가. 새 섹션, 새 요구사항, 적용 범위 확대.
- RESTRUCTURED: 내용은 동일하나 위치/구조/번호 변경. 섹션 이동, 번호 재부여 등.

## 판단 기준

1. 수치 변경은 "의무 vs 허용" 관점으로 판단:
   - 시스템이 달성해야 할 의무가 늘어남 → STRICTER
     예: "응답 시간 3초→1초" (더 빠르게 응답해야 함), "동시 접속 50명→100명" (더 많은 사용자를 지원해야 함), "보관 기간 5년→10년" (더 오래 보관해야 함)
   - 사용자/운영자에 대한 제약이 줄어듦 → MORE_LENIENT
     예: "백업 매일→매주" (백업 빈도 의무 감소), "테스트 커버리지 80%→70%" (기준 완화), "업로드 제한 10MB→50MB" (사용자 허용 범위 확대)
2. 단순 표현 변경(~하며/~하고, 이를/이 문제를)은 EDITORIAL
3. 새 문장/절이 추가되어 기존 범위를 넘어서면 EXPANDED
4. 약어에 풀네임을 병기하는 것은 CLARIFICATION
5. 선택지가 추가되어 사용자의 선택 범위가 넓어진 경우("온프레미스"→"온프레미스 또는 클라우드")는 MORE_LENIENT

## 출력 규칙

각 변경에 대해 반드시 아래 JSON 형식으로 응답하세요:
- tag: 6종 태그 중 하나 (대문자 영어)
- confidence: 0.0~1.0 사이의 확신도
- explanation: 한국어 1문장으로 분류 이유 설명"""


# ── 3. Few-shot 예시 ──

FEW_SHOT_EXAMPLES = """## 예시

입력:
[
  {"index": 0, "type": "modified", "text_a": "시스템 가용성은 99.5%를 보장한다.", "text_b": "시스템 가용성은 99.9%를 보장한다."},
  {"index": 1, "type": "modified", "text_a": "관리자는 사용자 권한을 설정한다.", "text_b": "관리자(Admin)는 사용자 권한을 설정한다."},
  {"index": 2, "type": "added", "text_a": null, "text_b": "4.1 감사 로그: 모든 데이터 변경 이력을 90일간 보관한다."},
  {"index": 3, "type": "modified", "text_a": "시스템은 동시 접속 사용자 200명을 지원해야 한다.", "text_b": "시스템은 동시 접속 사용자 500명을 지원해야 한다."},
  {"index": 4, "type": "modified", "text_a": "첨부파일 최대 크기는 5MB이다.", "text_b": "첨부파일 최대 크기는 20MB이다."}
]

출력:
[
  {"index": 0, "tag": "STRICTER", "confidence": 0.95, "explanation": "가용성 기준이 99.5%에서 99.9%로 강화되었습니다."},
  {"index": 1, "tag": "CLARIFICATION", "confidence": 0.9, "explanation": "관리자에 영문 약어(Admin)를 병기하여 의미를 명확히 했습니다."},
  {"index": 2, "tag": "EXPANDED", "confidence": 0.95, "explanation": "감사 로그 보관 요구사항이 새로 추가되었습니다."},
  {"index": 3, "tag": "STRICTER", "confidence": 0.9, "explanation": "시스템이 지원해야 하는 동시 접속 수가 200명에서 500명으로 강화되었습니다."},
  {"index": 4, "tag": "MORE_LENIENT", "confidence": 0.9, "explanation": "사용자가 업로드할 수 있는 최대 파일 크기가 5MB에서 20MB로 완화되었습니다."}
]"""


# ── 4. JSON 스키마 (Ollama format 파라미터용) ──

JSON_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "index": {"type": "integer"},
            "tag": {
                "type": "string",
                "enum": ["EDITORIAL", "CLARIFICATION", "STRICTER",
                         "MORE_LENIENT", "EXPANDED", "RESTRUCTURED"]
            },
            "confidence": {"type": "number"},
            "explanation": {"type": "string"}
        },
        "required": ["index", "tag", "confidence", "explanation"]
    }
}


def build_prompt(changes: list[dict]) -> str:
    """사용자 프롬프트 조립: few-shot + 변경 구간 데이터"""
    items = []
    for c in changes:
        item = {"index": c["index"], "type": c["type"]}
        if c["text_a"]:
            item["text_a"] = c["text_a"]
        else:
            item["text_a"] = None
        if c["text_b"]:
            item["text_b"] = c["text_b"]
        else:
            item["text_b"] = None
        items.append(item)

    return f"""{FEW_SHOT_EXAMPLES}

---

아래 변경 구간을 분류하세요:

{json.dumps(items, ensure_ascii=False, indent=2)}"""


def call_ollama(model: str, prompt: str, system: str) -> tuple[dict | None, float]:
    """Ollama 호출 → (파싱된 JSON, 응답시간초)"""
    payload = {
        "model": model,
        "prompt": prompt,
        "system": system,
        "stream": False,
        "format": JSON_SCHEMA,
        "options": {"temperature": 0}
    }

    start = time.time()
    try:
        resp = httpx.post(
            f"{OLLAMA_URL}/api/generate",
            json=payload,
            timeout=120.0
        )
        elapsed = time.time() - start
        data = resp.json()
        raw = data.get("response", "")

        try:
            parsed = json.loads(raw)
            return parsed, elapsed
        except json.JSONDecodeError as e:
            print(f"  [JSON 파싱 실패] {e}")
            print(f"  [원본 응답] {raw[:500]}")
            return None, elapsed
    except Exception as e:
        elapsed = time.time() - start
        print(f"  [호출 실패] {e}")
        return None, elapsed


def evaluate(results: list[dict], changes: list[dict]) -> dict:
    """분류 정확도 평가"""
    if not results:
        return {"accuracy": 0, "correct": 0, "total": len(changes), "details": []}

    result_map = {r["index"]: r for r in results}
    correct = 0
    details = []

    for c in changes:
        r = result_map.get(c["index"])
        if not r:
            details.append({"index": c["index"], "expected": c["expected_tag"],
                          "actual": "MISSING", "correct": False})
            continue

        is_correct = r.get("tag") == c["expected_tag"]
        if is_correct:
            correct += 1
        details.append({
            "index": c["index"],
            "expected": c["expected_tag"],
            "actual": r.get("tag", "?"),
            "confidence": r.get("confidence", 0),
            "explanation": r.get("explanation", ""),
            "correct": is_correct
        })

    return {
        "accuracy": correct / len(changes),
        "correct": correct,
        "total": len(changes),
        "details": details
    }


def run_test(model: str, changes: list[dict], batch_size: int = 20):
    """단일 모델 테스트 실행"""
    print(f"\n{'='*60}")
    print(f"모델: {model} | 변경 {len(changes)}건 | 배치 {batch_size}")
    print(f"{'='*60}")

    # 배치 분할
    all_results = []
    total_time = 0

    for i in range(0, len(changes), batch_size):
        batch = changes[i:i+batch_size]
        print(f"\n  배치 {i//batch_size + 1}: {len(batch)}건 처리 중...")

        prompt = build_prompt(batch)
        results, elapsed = call_ollama(model, prompt, SYSTEM_PROMPT)
        total_time += elapsed

        if results:
            all_results.extend(results)
            print(f"  → {len(results)}건 분류 완료 ({elapsed:.1f}초)")
        else:
            print(f"  → 실패 ({elapsed:.1f}초)")

    # 평가
    eval_result = evaluate(all_results, changes)

    print(f"\n{'─'*60}")
    print(f"결과: {eval_result['correct']}/{eval_result['total']} 정확 "
          f"({eval_result['accuracy']*100:.0f}%)")
    print(f"총 소요 시간: {total_time:.1f}초")
    print(f"{'─'*60}")

    # 상세 결과
    for d in eval_result["details"]:
        mark = "O" if d["correct"] else "X"
        conf = f" ({d.get('confidence', 0):.2f})" if d.get("confidence") else ""
        expl = d.get("explanation", "")
        print(f"  {mark} [{d['index']:2d}] expected={d['expected']:14s} "
              f"actual={d['actual']:14s}{conf}  {expl}")

    return {
        "model": model,
        "changes_count": len(changes),
        "elapsed_seconds": round(total_time, 1),
        "json_parse_success": len(all_results) > 0,
        "accuracy": eval_result["accuracy"],
        "correct": eval_result["correct"],
        "total": eval_result["total"],
        "details": eval_result["details"]
    }


if __name__ == "__main__":
    print("Phase 6-0 v2: AI 의미 분류 (6태그, NUMERIC 폐지)")
    print("=" * 60)

    # 테스트 시나리오
    tests = [
        ("gemma3:4b", 5),    # 4B + 작은 배치
        ("gemma3:12b", 5),   # 12B + 작은 배치
        ("gemma3:12b", 15),  # 12B + 전체 배치
    ]

    all_reports = []
    for model, batch in tests:
        report = run_test(model, SAMPLE_CHANGES, batch_size=batch)
        all_reports.append(report)

    # 결과 JSON 저장
    output_path = "workbench/phase6-0-results-v2.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "test_date": time.strftime("%Y-%m-%d %H:%M"),
            "system_prompt_length": len(SYSTEM_PROMPT),
            "few_shot_examples": 3,
            "sample_changes": len(SAMPLE_CHANGES),
            "json_schema_used": True,
            "reports": all_reports
        }, f, ensure_ascii=False, indent=2)

    print(f"\n결과 저장: {output_path}")
