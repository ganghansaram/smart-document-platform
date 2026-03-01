"""
키워드 기반 검색 서비스
"""
import json
from pathlib import Path
from typing import List

import config

def load_search_index():
    """검색 인덱스 로드"""
    index_path = Path(__file__).parent.parent / config.SEARCH_INDEX_PATH
    if not index_path.exists():
        return []

    with open(index_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def search_documents(query: str, top_k: int = 5) -> List[dict]:
    """
    키워드 기반 문서 검색
    """
    index = load_search_index()
    if not index:
        return []

    # 쿼리를 단어로 분리
    terms = [t.lower() for t in query.split() if len(t) >= 2]
    if not terms:
        return []

    results = []
    for doc in index:
        title_lower = doc.get('title', '').lower()
        content_lower = doc.get('content', '').lower()
        score = 0

        for term in terms:
            if term in title_lower:
                score += 10
            if term in content_lower:
                score += 1

        if score > 0:
            results.append({
                'title': doc.get('title', ''),
                'content': doc.get('content', '')[:1600],
                'path': doc.get('url', ''),
                'section_id': doc.get('section_id'),
                'score': score
            })

    # 점수순 정렬
    results.sort(key=lambda x: -x['score'])
    return results[:top_k]
