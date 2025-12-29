"""
Embedding generation for the Agentic Analytics Platform.
Uses SentenceTransformers for local embedding generation.
"""

import time
from dataclasses import dataclass
from typing import List, Optional, Union
import numpy as np

from src.utils.config import get_settings
from src.utils.helpers import duration_ms
from src.observability.latency import get_latency_tracker, OperationType


@dataclass
class EmbeddingResult:
    """Result of an embedding operation."""
    embeddings: np.ndarray
    model_name: str
    dimension: int
    count: int
    duration_ms: float


class EmbeddingModel:
    """
    Embedding model using SentenceTransformers.
    Provides efficient batch embedding with caching.
    """
    
    def __init__(self, model_name: Optional[str] = None):
        settings = get_settings()
        self._model_name = model_name or settings.data.embedding_model
        self._model = None
        self._dimension: Optional[int] = None
        self._latency_tracker = get_latency_tracker()
    
    def _load_model(self):
        """Lazy-load the embedding model."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self._model_name)
                # Get embedding dimension from a test embedding
                test_embedding = self._model.encode(["test"], convert_to_numpy=True)
                self._dimension = test_embedding.shape[1]
            except ImportError:
                # Fallback to simple hash-based embeddings for testing
                self._model = "fallback"
                self._dimension = 384  # Standard dimension
    
    @property
    def dimension(self) -> int:
        """Get the embedding dimension."""
        if self._dimension is None:
            self._load_model()
        return self._dimension
    
    @property
    def model_name(self) -> str:
        return self._model_name
    
    def embed(self, texts: Union[str, List[str]], trace_id: Optional[str] = None) -> EmbeddingResult:
        """
        Generate embeddings for text(s).
        
        Args:
            texts: Single text or list of texts to embed
            trace_id: Optional trace ID for observability
        
        Returns:
            EmbeddingResult with embeddings and metadata
        """
        self._load_model()
        
        # Normalize input
        if isinstance(texts, str):
            texts = [texts]
        
        start_time = time.perf_counter()
        
        if self._model == "fallback":
            # Fallback: simple hash-based embeddings for testing without dependencies
            embeddings = self._fallback_embed(texts)
        else:
            # Use SentenceTransformer
            embeddings = self._model.encode(
                texts,
                convert_to_numpy=True,
                show_progress_bar=False
            )
        
        elapsed = duration_ms(start_time)
        
        # Record latency
        self._latency_tracker.record(
            operation=OperationType.EMBEDDING,
            duration_ms=elapsed,
            trace_id=trace_id,
            metadata={"count": len(texts), "model": self._model_name}
        )
        
        return EmbeddingResult(
            embeddings=embeddings,
            model_name=self._model_name,
            dimension=self._dimension,
            count=len(texts),
            duration_ms=elapsed
        )
    
    def _fallback_embed(self, texts: List[str]) -> np.ndarray:
        """
        Fallback embedding using hash-based vectors.
        Only for testing when SentenceTransformers is not installed.
        """
        embeddings = []
        for text in texts:
            # Create deterministic pseudo-random vector from text hash
            np.random.seed(hash(text) % (2**32))
            vec = np.random.randn(self._dimension).astype(np.float32)
            # Normalize to unit vector
            vec = vec / np.linalg.norm(vec)
            embeddings.append(vec)
        return np.array(embeddings)
    
    def embed_single(self, text: str, trace_id: Optional[str] = None) -> np.ndarray:
        """Embed a single text and return the vector."""
        result = self.embed(text, trace_id)
        return result.embeddings[0]
    
    def embed_batch(self, texts: List[str], batch_size: int = 32,
                    trace_id: Optional[str] = None) -> EmbeddingResult:
        """
        Embed texts in batches for memory efficiency.
        
        Args:
            texts: List of texts to embed
            batch_size: Batch size for processing
            trace_id: Optional trace ID
        
        Returns:
            Combined EmbeddingResult
        """
        self._load_model()
        
        start_time = time.perf_counter()
        all_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            if self._model == "fallback":
                batch_embeddings = self._fallback_embed(batch)
            else:
                batch_embeddings = self._model.encode(
                    batch,
                    convert_to_numpy=True,
                    show_progress_bar=False
                )
            all_embeddings.append(batch_embeddings)
        
        embeddings = np.vstack(all_embeddings)
        elapsed = duration_ms(start_time)
        
        return EmbeddingResult(
            embeddings=embeddings,
            model_name=self._model_name,
            dimension=self._dimension,
            count=len(texts),
            duration_ms=elapsed
        )


# Singleton model instance
_embedding_model: Optional[EmbeddingModel] = None


def get_embedding_model() -> EmbeddingModel:
    """Get the global embedding model instance."""
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = EmbeddingModel()
    return _embedding_model


def embed_texts(texts: Union[str, List[str]], trace_id: Optional[str] = None) -> np.ndarray:
    """
    Convenience function to embed texts.
    
    Args:
        texts: Text(s) to embed
        trace_id: Optional trace ID
    
    Returns:
        Numpy array of embeddings
    """
    model = get_embedding_model()
    result = model.embed(texts, trace_id)
    return result.embeddings
