from typing import Any, Dict, List, Optional
import hashlib
import re


class SimpleMetadataStore:
    _documents: List[Dict[str, Any]] = []
    _index: Dict[str, int] = {}

    @classmethod
    def reset(cls):
        cls._documents = []
        cls._index = {}

    @classmethod
    def add_document(cls, doc_id: str, text: str, metadata: Dict[str, Any]) -> None:
        if doc_id in cls._index:
            return
        cls._index[doc_id] = len(cls._documents)
        cls._documents.append({
            "id": doc_id,
            "text": text,
            "metadata": metadata,
            "tokens": set(re.findall(r"[a-z0-9_]+", text.lower()))
        })

    @classmethod
    def search(cls, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        query_tokens = set(re.findall(r"[a-z0-9_]+", query.lower()))
        scored = []
        for doc in cls._documents:
            overlap = len(query_tokens & doc["tokens"])
            if overlap > 0:
                scored.append((overlap, doc))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [doc for _, doc in scored[:top_k]]

    @classmethod
    def get_document(cls, doc_id: str) -> Optional[Dict[str, Any]]:
        idx = cls._index.get(doc_id)
        if idx is not None:
            return cls._documents[idx]
        return None

    @classmethod
    def all_documents(cls) -> List[Dict[str, Any]]:
        return list(cls._documents)
