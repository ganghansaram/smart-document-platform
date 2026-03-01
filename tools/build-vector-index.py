#!/usr/bin/env python3
"""
벡터 인덱스 생성 스크립트
search-index.json → FAISS 인덱스 + 메타데이터
"""
import json
import sys
import time
from pathlib import Path

# backend 모듈 import를 위한 경로 추가
BACKEND_DIR = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

import numpy as np
import config
from services.embedding_client import get_embeddings


def load_search_index() -> list:
    """search-index.json 로드"""
    index_path = BACKEND_DIR / config.SEARCH_INDEX_PATH
    if not index_path.exists():
        print(f"[ERROR] 검색 인덱스 없음: {index_path}")
        sys.exit(1)

    with open(index_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"[INFO] 검색 인덱스 로드: {len(data)}개 문서")
    return data


def build_texts(docs: list) -> list[str]:
    """임베딩할 텍스트 생성 (title + content)"""
    texts = []
    for doc in docs:
        title = doc.get("title", "")
        content = doc.get("content", "")
        # 제목에 가중치를 주기 위해 제목을 반복 포함
        text = f"{title}\n{title}\n{content}"
        texts.append(text)
    return texts


def batch_embed(texts: list[str], batch_size: int = 32) -> np.ndarray:
    """배치 단위로 임베딩 생성"""
    all_embeddings = []
    total = len(texts)

    for i in range(0, total, batch_size):
        batch = texts[i:i + batch_size]
        print(f"  임베딩 중... [{i + 1}-{min(i + batch_size, total)}/{total}]")
        embeddings = get_embeddings(batch)
        all_embeddings.extend(embeddings)

    return np.array(all_embeddings, dtype=np.float32)


def build_and_save_index(docs: list, embeddings: np.ndarray):
    """FAISS 인덱스 생성 및 저장"""
    import faiss

    dimension = embeddings.shape[1]
    print(f"[INFO] 임베딩 차원: {dimension}, 문서 수: {embeddings.shape[0]}")

    # L2 인덱스 (문서 수가 적으므로 Flat으로 충분)
    index = faiss.IndexFlatL2(dimension)
    # 정규화 후 Inner Product 대신, L2로 가도 성능 충분 (문서 수 < 10k)
    index.add(embeddings)

    # 저장 경로
    base_path = BACKEND_DIR / config.VECTOR_INDEX_PATH
    base_path.parent.mkdir(parents=True, exist_ok=True)

    faiss_path = str(base_path) + ".faiss"
    meta_path = str(base_path) + "_meta.json"

    faiss.write_index(index, faiss_path)
    print(f"[INFO] FAISS 인덱스 저장: {faiss_path}")

    # 메타데이터 저장 (인덱스 순서와 동일)
    metadata = []
    for doc in docs:
        metadata.append({
            "title": doc.get("title", ""),
            "content": doc.get("content", "")[:500],
            "url": doc.get("url", ""),
            "section_id": doc.get("section_id"),
            "path": doc.get("path", ""),
        })

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    print(f"[INFO] 메타데이터 저장: {meta_path}")


def main():
    print("=" * 50)
    print("벡터 인덱스 생성")
    print(f"임베딩 모델: {config.EMBEDDING_MODEL}")
    print(f"Ollama URL: {config.OLLAMA_URL}")
    print("=" * 50)

    start = time.time()

    # 1. 검색 인덱스 로드
    docs = load_search_index()

    # 빈 content 문서 필터링
    valid_docs = [d for d in docs if d.get("content", "").strip()]
    print(f"[INFO] 유효 문서 (content 있음): {len(valid_docs)}/{len(docs)}")

    if not valid_docs:
        print("[ERROR] 유효한 문서가 없습니다.")
        sys.exit(1)

    # 2. 텍스트 생성
    texts = build_texts(valid_docs)

    # 3. 임베딩 생성
    print("[INFO] 임베딩 생성 시작...")
    embeddings = batch_embed(texts)

    # 4. FAISS 인덱스 빌드 및 저장
    build_and_save_index(valid_docs, embeddings)

    elapsed = time.time() - start
    print(f"\n[DONE] 완료 ({elapsed:.1f}초)")


if __name__ == "__main__":
    main()
