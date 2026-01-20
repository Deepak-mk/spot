"""
Vector store for the Agentic Analytics Platform.
Provides semantic search using FAISS or in-memory fallback.
"""

import json
import time
import pickle
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple
from pathlib import Path
import numpy as np

from src.utils.config import get_settings
from src.utils.helpers import duration_ms
from src.retrieval.embeddings import get_embedding_model, embed_texts
from src.observability.latency import get_latency_tracker, OperationType


@dataclass
class SearchResult:
    """A single search result."""
    document_id: str
    content: str
    score: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "document_id": self.document_id,
            "content": self.content,
            "score": round(self.score, 4),
            "metadata": self.metadata,
        }


@dataclass
class Document:
    """A document in the vector store."""
    id: str
    content: str
    embedding: np.ndarray
    metadata: Dict[str, Any] = field(default_factory=dict)


class VectorStore:
    """
    Vector store for semantic search.
    Uses FAISS for efficient similarity search with in-memory fallback.
    """
    
    def __init__(self, persist_path: Optional[str] = None):
        settings = get_settings()
        self._persist_path = Path(persist_path) if persist_path else Path(settings.vector_store_path)
        self._persist_path.mkdir(parents=True, exist_ok=True)
        
        self._documents: Dict[str, Document] = {}
        self._id_to_idx: Dict[str, int] = {}
        self._idx_to_id: Dict[int, str] = {}
        self._embeddings: Optional[np.ndarray] = None
        self._index = None  # FAISS index
        self._use_faiss = False
        self._latency_tracker = get_latency_tracker()
        
        self._try_load_faiss()
        
        # Try to load persisted data
        self.load()
    
    def _try_load_faiss(self):
        """Try to load FAISS, fall back to numpy if not available."""
        try:
            import faiss
            self._use_faiss = True
        except ImportError:
            self._use_faiss = False
    
    def add_documents(
        self,
        documents: List[Dict[str, Any]],
        trace_id: Optional[str] = None
    ) -> int:
        """
        Add documents to the vector store.
        
        Args:
            documents: List of dicts with 'id', 'content', and optional 'metadata'
            trace_id: Optional trace ID for observability
        
        Returns:
            Number of documents added
        """
        if not documents:
            return 0
        
        start_time = time.perf_counter()
        
        # Extract content for embedding
        contents = [doc["content"] for doc in documents]
        
        # Generate embeddings
        embedding_model = get_embedding_model()
        result = embedding_model.embed(contents, trace_id)
        embeddings = result.embeddings
        
        # Store documents
        start_idx = len(self._documents)
        for i, doc in enumerate(documents):
            doc_id = doc["id"]
            document = Document(
                id=doc_id,
                content=doc["content"],
                embedding=embeddings[i],
                metadata=doc.get("metadata", {})
            )
            self._documents[doc_id] = document
            idx = start_idx + i
            self._id_to_idx[doc_id] = idx
            self._idx_to_id[idx] = doc_id
        
        # Rebuild index
        self._rebuild_index()
        
        elapsed = duration_ms(start_time)
        self._latency_tracker.record(
            operation=OperationType.RETRIEVAL,
            duration_ms=elapsed,
            trace_id=trace_id,
            metadata={"action": "add_documents", "count": len(documents)}
        )
        
        return len(documents)
    
    def _rebuild_index(self):
        """Rebuild the vector index from all documents."""
        if not self._documents:
            self._embeddings = None
            self._index = None
            return
        
        # Stack all embeddings
        embeddings_list = []
        for idx in range(len(self._documents)):
            doc_id = self._idx_to_id[idx]
            embeddings_list.append(self._documents[doc_id].embedding)
        
        self._embeddings = np.vstack(embeddings_list).astype(np.float32)
        
        if self._use_faiss:
            import faiss
            dimension = self._embeddings.shape[1]
            self._index = faiss.IndexFlatIP(dimension)  # Inner product (cosine after normalization)
            # Normalize for cosine similarity
            faiss.normalize_L2(self._embeddings)
            self._index.add(self._embeddings)
    
    def search(
        self,
        query: str,
        top_k: int = 5,
        trace_id: Optional[str] = None,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """
        Search for similar documents.
        
        Args:
            query: Search query
            top_k: Number of results to return
            trace_id: Optional trace ID
            filter_metadata: Optional metadata filter
        
        Returns:
            List of SearchResult objects
        """
        if not self._documents:
            return []
        
        start_time = time.perf_counter()
        
        # Embed query
        query_embedding = embed_texts(query, trace_id)[0].astype(np.float32)
        
        if self._use_faiss:
            results = self._search_faiss(query_embedding, top_k, filter_metadata)
        else:
            results = self._search_numpy(query_embedding, top_k, filter_metadata)
        
        elapsed = duration_ms(start_time)
        self._latency_tracker.record(
            operation=OperationType.RETRIEVAL,
            duration_ms=elapsed,
            trace_id=trace_id,
            metadata={"action": "search", "query_length": len(query), "top_k": top_k}
        )
        
        return results
    
    def _search_faiss(
        self,
        query_embedding: np.ndarray,
        top_k: int,
        filter_metadata: Optional[Dict] = None
    ) -> List[SearchResult]:
        """Search using FAISS index."""
        import faiss
        
        # Normalize query for cosine similarity
        query_embedding = query_embedding.reshape(1, -1)
        faiss.normalize_L2(query_embedding)
        
        # Get more results if filtering
        search_k = top_k * 3 if filter_metadata else top_k
        
        scores, indices = self._index.search(query_embedding, min(search_k, len(self._documents)))
        
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue
            
            doc_id = self._idx_to_id[idx]
            doc = self._documents[doc_id]
            
            # Apply metadata filter
            if filter_metadata:
                if not self._matches_filter(doc.metadata, filter_metadata):
                    continue
            
            results.append(SearchResult(
                document_id=doc_id,
                content=doc.content,
                score=float(score),
                metadata=doc.metadata
            ))
            
            if len(results) >= top_k:
                break
        
        return results
    
    def _search_numpy(
        self,
        query_embedding: np.ndarray,
        top_k: int,
        filter_metadata: Optional[Dict] = None
    ) -> List[SearchResult]:
        """Search using numpy (fallback)."""
        # Normalize query
        query_norm = query_embedding / np.linalg.norm(query_embedding)
        
        # Compute cosine similarity with all documents
        similarities = []
        for doc_id, doc in self._documents.items():
            # Apply metadata filter
            if filter_metadata:
                if not self._matches_filter(doc.metadata, filter_metadata):
                    continue
            
            doc_norm = doc.embedding / np.linalg.norm(doc.embedding)
            score = float(np.dot(query_norm, doc_norm))
            similarities.append((doc_id, score))
        
        # Sort by score descending
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        results = []
        for doc_id, score in similarities[:top_k]:
            doc = self._documents[doc_id]
            results.append(SearchResult(
                document_id=doc_id,
                content=doc.content,
                score=score,
                metadata=doc.metadata
            ))
        
        return results
    
    def _matches_filter(self, metadata: Dict, filter_dict: Dict) -> bool:
        """Check if metadata matches filter criteria."""
        for key, value in filter_dict.items():
            if key not in metadata:
                return False
            if metadata[key] != value:
                return False
        return True
    
    def get_document(self, doc_id: str) -> Optional[Document]:
        """Get a document by ID."""
        return self._documents.get(doc_id)
    
    def delete_document(self, doc_id: str) -> bool:
        """Delete a document. Note: Requires index rebuild."""
        if doc_id not in self._documents:
            return False
        
        del self._documents[doc_id]
        
        # Rebuild mappings
        self._id_to_idx.clear()
        self._idx_to_id.clear()
        for i, did in enumerate(self._documents.keys()):
            self._id_to_idx[did] = i
            self._idx_to_id[i] = did
        
        self._rebuild_index()
        return True
    
    def count(self) -> int:
        """Get number of documents in the store."""
        return len(self._documents)
    
    def save(self, path: Optional[str] = None) -> str:
        """Save the vector store to disk."""
        save_path = Path(path) if path else self._persist_path / "vector_store.pkl"
        
        data = {
            "documents": {doc_id: {
                "id": doc.id,
                "content": doc.content,
                "embedding": doc.embedding,
                "metadata": doc.metadata
            } for doc_id, doc in self._documents.items()},
            "id_to_idx": self._id_to_idx,
            "idx_to_id": self._idx_to_id,
        }
        
        with open(save_path, 'wb') as f:
            pickle.dump(data, f)
        
        return str(save_path)
    
    def load(self, path: Optional[str] = None) -> bool:
        """Load the vector store from disk."""
        load_path = Path(path) if path else self._persist_path / "vector_store.pkl"
        
        if not load_path.exists():
            return False
        
        with open(load_path, 'rb') as f:
            data = pickle.load(f)
        
        self._documents = {
            doc_id: Document(
                id=doc_data["id"],
                content=doc_data["content"],
                embedding=doc_data["embedding"],
                metadata=doc_data["metadata"]
            )
            for doc_id, doc_data in data["documents"].items()
        }
        self._id_to_idx = data["id_to_idx"]
        self._idx_to_id = data["idx_to_id"]
        
        self._rebuild_index()
        return True
    
    def clear(self):
        """Clear all documents from the store."""
        self._documents.clear()
        self._id_to_idx.clear()
        self._idx_to_id.clear()
        self._embeddings = None
        self._index = None


# Singleton instance
_vector_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """Get the global vector store instance."""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
