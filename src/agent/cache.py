import json
import os
import numpy as np
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from pathlib import Path
from src.retrieval.embeddings import get_embedding_model

@dataclass
class CacheEntry:
    query: str
    sql_query: str
    sql_result: Dict[str, Any]
    answer: str
    embedding: List[float]
    timestamp: float

class SemanticCache:
    """
    Semantic Cache for Agentic Analytics.
    Stores {embedding, query, response} to avoid re-generating SQL for similar queries.
    """
    def __init__(self, persistence_path: str = "config/semantic_cache.json"):
        self.persistence_path = persistence_path
        self._entries: List[CacheEntry] = []
        self._embedding_model = get_embedding_model()
        self._threshold = 0.95
        self._load()

    def lookup(self, query: str) -> Optional[Dict]:
        """
        Look for a semantically similar query in the cache.
        Returns the cached AgentResponse dict data if found.
        """
        if not self._entries:
            return None
        
        # Embed current query
        query_vec = self._embedding_model.embed_single(query)
        
        # Calculate cosine similarity with all entries
        # Optimized: usage matrix multiplication if possible, but loop is fine for <1000 items
        best_score = -1.0
        best_entry = None
        
        query_norm = query_vec / np.linalg.norm(query_vec)
        
        for entry in self._entries:
            entry_vec = np.array(entry.embedding)
            entry_norm = entry_vec / np.linalg.norm(entry_vec)
            score = np.dot(query_norm, entry_norm)
            
            if score > best_score:
                best_score = score
                best_entry = entry
                
        if best_entry and best_score >= self._threshold:
            print(f"⚡ Cache Hit! Query: '{query}' ~= '{best_entry.query}' (Score: {best_score:.4f})")
            return {
                "query": query,
                "answer": best_entry.answer,
                "sql_query": best_entry.sql_query,
                "sql_result": best_entry.sql_result,
                "is_cached": True,
                "similarity_score": float(best_score)
            }
            
        return None

    def store(self, query: str, sql_query: str, sql_result: Dict, answer: str) -> None:
        """Store a successful query result."""
        import time
        
        # Verify it's not already covered
        if self.lookup(query):
            return

        embedding = self._embedding_model.embed_single(query)
        
        entry = CacheEntry(
            query=query,
            sql_query=sql_query,
            sql_result=sql_result,
            answer=answer,
            embedding=embedding.tolist(),
            timestamp=time.time()
        )
        self._entries.append(entry)
        self._save()
        print(f"💾 Cached new query: '{query}'")

    def _save(self):
        """Persist cache to disk."""
        data = [
            {
                "query": e.query,
                "sql_query": e.sql_query,
                "sql_result": e.sql_result,
                "answer": e.answer,
                "embedding": e.embedding,
                "timestamp": e.timestamp
            }
            for e in self._entries
        ]
        Path(self.persistence_path).parent.mkdir(exist_ok=True)
        with open(self.persistence_path, "w") as f:
            json.dump(data, f)

    def _load(self):
        """Load cache from disk."""
        if not os.path.exists(self.persistence_path):
            return
            
        try:
            with open(self.persistence_path, "r") as f:
                data = json.load(f)
                self._entries = [
                    CacheEntry(**item) for item in data
                ]
            print(f"Loaded {len(self._entries)} cached queries.")
        except Exception as e:
            print(f"Failed to load cache: {e}")

# Singleton
_cache: Optional[SemanticCache] = None

def get_semantic_cache() -> SemanticCache:
    global _cache
    if _cache is None:
        _cache = SemanticCache()
    return _cache
