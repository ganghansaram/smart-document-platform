# Similarity Goldset (Plan-38 Phase 0)

K-SPEC 1:1 표절검토 시스템(Plan-38)의 분류 정확도 측정용 합성 골드셋.

## 출처 및 방법론

PAN @ CLEF 표절 탐지 워크숍(2009~2015)에서 사용된 **PAN-PC (Plagiarism Corpus)**
방법론 채택 — 하나의 원문 시드에서 여러 obfuscation strategy를 인위적으로 합성하여
탐지 알고리즘을 평가하는 표준 방식.

본 골드셋은 K-SPEC 도메인(군사 항공전자 기술표준)에 맞게 자체 작성된 합성 코퍼스로,
실제 MIL-STD 문서를 인용하지 않고 **문체와 구조만 모사**하였다.

## 디렉토리 구조

```
data/similarity-goldset/
├── seeds/                    # 원문 시드 3종
│   ├── seed_a_emc.md         # EMC/EMI 시험 (영문, 652단어)
│   ├── seed_a_emc_ko.md      # 시드 A 한국어 번역 (493단어)
│   └── seed_b_env.md         # 환경시험 (영문, 671단어)
├── variants/                 # 변형 12종
│   ├── var_a_verbatim.md     # 시드 A 그대로 복사
│   ├── var_a_random_obf.md   # 단어 30% 동의어 치환
│   ├── var_a_para_light.md   # 경량 의역 (구조 유지)
│   ├── var_a_para_heavy.md   # 중량 의역 (재구성)
│   ├── var_a_cyclic_trans.md # 한↔영 역번역 풍
│   ├── var_a_boilerplate.md  # 정형구문 80% 삽입
│   └── var_b_*.md            # 시드 B 동일 6종 (direct_trans 제외)
├── pairs/                    # 페어별 골드 라벨 14건
│   └── pair_NN_*.json
├── generate_pairs.py         # 페어 JSON 생성 스크립트
└── README.md                 # 본 파일
```

## 페어 구성 (총 14건)

| ID | 변형 | 시드 | 기대 점수 | 기대 신호등 |
|---|---|---|---|---|
| pair_01 | verbatim | A | 85~100% | Red |
| pair_02 | random_obf | A | 50~90% | Orange |
| pair_03 | para_light | A | 25~75% | Yellow/Orange |
| pair_04 | para_heavy | A | 15~60% | Yellow |
| pair_05 | cyclic_trans | A | 25~70% | Yellow |
| pair_06 | direct_trans (KO↔EN) | A | 20~60% | Yellow |
| pair_07 | boilerplate | A | 0~30% | Green/Blue |
| pair_08~13 | 시드 B 6변형 (direct_trans 제외) | B | 동일 | 동일 |
| pair_14 | no_plagiarism (A vs B) | A,B | 0~25% | Blue/Green |

## 평가 방법

### 사전 조건
- bge-m3 임베딩 모델 (`models/bge-m3/` 또는 Ollama)
- sentence-transformers 라이브러리
- `backend/` 의존 패키지

### 실행
```bash
# 모든 페어 평가
PYTHONPATH=backend python tools/eval/similarity_eval.py

# 특정 페어만
PYTHONPATH=backend python tools/eval/similarity_eval.py --pair pair_01

# 상세 결과 JSON 저장
PYTHONPATH=backend python tools/eval/similarity_eval.py --json /tmp/sim-eval.json
```

### 종료 코드
- 0: 모든 페어 통과
- 1: 일부 실패 (캘리브레이션 필요)
- 2: 실행 오류 (모델 로드 실패 등)

## 검증 기준

각 페어는 4가지 기준을 통과해야 PASS:
1. **점수 대역 적중** — `tiers.adjusted`가 `expected_score_range` 안에
2. **라벨 분포 적중** — 각 라벨 비율이 `expected_label_distribution` 범위에
3. **최소 매칭 수** — `len(matches) >= min_match_count`
4. **보일러플레이트 비율** (해당 페어만) — `>= expected_boilerplate_ratio_min`

## 갱신·확장

새 변형 추가 시:
1. `variants/var_X_<name>.md` 작성 (또는 시드 추가)
2. `generate_pairs.py`에 페어 정의 추가
3. `python generate_pairs.py` 실행하여 JSON 생성
4. 평가 스크립트로 검증

실 사용 1개월 후, 실제 K-SPEC 사례를 기반으로 임계값 재캘리브레이션 권장.

## 라이선스

본 골드셋의 모든 시드·변형 텍스트는 자체 창작물(CC0)이다. 실제 MIL-STD 또는
타 표준서의 원문을 포함하지 않으며, 문체·구조만 도메인 정합성을 위해 모사하였다.

## 참고

- Potthast, Stein et al. — *PAN Plagiarism Corpus 2011 (PAN-PC-11)*
- PAN @ CLEF 워크숍 시리즈 (https://pan.webis.de/)
- Plan-38 본문: `workbench/plans/38-similarity-plagiarism-grade.md`
