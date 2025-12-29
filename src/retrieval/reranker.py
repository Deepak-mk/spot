"""
Re-ranking for the Agentic Analytics Platform.
Re-ranks search results for better relevance.
"""

from dataclasses import dataclass
from typing import List, Optional, Callable
from src.retrieval.vector_store import SearchResult


@dataclass
class RerankedResult:
    """A re-ranked search result."""
    result: SearchResult
    original_rank: int
    new_rank: int
    rerank_score: float


class Reranker:
    """
    Re-ranks search results based on additional criteria.
    Can use score boosting, metadata preferences, or custom scoring.
    """
    
    def __init__(self):
        self._boost_factors: dict = {
            "table": 1.2,      # Boost table-level matches
            "metric": 1.3,    # Boost metric matches (most relevant)
            "column": 1.0,
            "relationship": 0.9,
            "query": 1.1,     # Sample queries are helpful
        }
    
    def rerank(
        self,
        results: List[SearchResult],
        query: Optional[str] = None,
        top_k: Optional[int] = None,
        boost_chunk_types: Optional[dict] = None
    ) -> List[SearchResult]:
        """
        Re-rank search results.
        
        Args:
            results: Original search results
            query: Original query (for additional scoring)
            top_k: Max results to return
            boost_chunk_types: Optional custom boost factors by chunk type
        
        Returns:
            Re-ranked list of SearchResult
        """
        if not results:
            return []
        
        boost_factors = boost_chunk_types or self._boost_factors
        
        # Calculate rerank scores
        scored_results = []
        for i, result in enumerate(results):
            chunk_type = result.metadata.get("chunk_type", "")
            boost = boost_factors.get(chunk_type, 1.0)
            
            # Apply additional query-based scoring if query provided
            query_boost = 1.0
            if query:
                query_boost = self._query_relevance_boost(query, result)
            
            rerank_score = result.score * boost * query_boost
            scored_results.append((result, i, rerank_score))
        
        # Sort by rerank score descending
        scored_results.sort(key=lambda x: x[2], reverse=True)
        
        # Build reranked results
        reranked = []
        for new_rank, (result, original_rank, rerank_score) in enumerate(scored_results):
            # Create new result with updated score
            reranked_result = SearchResult(
                document_id=result.document_id,
                content=result.content,
                score=rerank_score,
                metadata={
                    **result.metadata,
                    "original_score": result.score,
                    "original_rank": original_rank,
                }
            )
            reranked.append(reranked_result)
        
        if top_k:
            return reranked[:top_k]
        return reranked
    
    def _query_relevance_boost(self, query: str, result: SearchResult) -> float:
        """
        Calculate additional boost based on query-result relevance.
        Simple keyword matching for now.
        """
        query_lower = query.lower()
        content_lower = result.content.lower()
        
        # Check for exact phrase match
        if query_lower in content_lower:
            return 1.3
        
        # Check for word overlap
        query_words = set(query_lower.split())
        content_words = set(content_lower.split())
        overlap = len(query_words & content_words)
        
        if overlap >= 3:
            return 1.2
        elif overlap >= 2:
            return 1.1
        elif overlap >= 1:
            return 1.05
        
        return 1.0
    
    def set_boost_factor(self, chunk_type: str, factor: float) -> None:
        """Set boost factor for a chunk type."""
        self._boost_factors[chunk_type] = factor
    
    def diversity_rerank(
        self,
        results: List[SearchResult],
        diversity_key: str = "chunk_type",
        top_k: int = 5
    ) -> List[SearchResult]:
        """
        Re-rank to maximize diversity of results.
        Ensures different types of content appear in results.
        
        Args:
            results: Original results
            diversity_key: Metadata key to diversify on
            top_k: Number of results to return
        
        Returns:
            Diversified results
        """
        if not results:
            return []
        
        # Group by diversity key
        groups: dict = {}
        for result in results:
            key = result.metadata.get(diversity_key, "other")
            if key not in groups:
                groups[key] = []
            groups[key].append(result)
        
        # Round-robin selection from groups
        diversified = []
        group_keys = list(groups.keys())
        indices = {key: 0 for key in group_keys}
        
        while len(diversified) < top_k:
            added = False
            for key in group_keys:
                if indices[key] < len(groups[key]):
                    diversified.append(groups[key][indices[key]])
                    indices[key] += 1
                    added = True
                    if len(diversified) >= top_k:
                        break
            
            if not added:
                break
        
        return diversified


# Singleton instance
_reranker: Optional[Reranker] = None


def get_reranker() -> Reranker:
    """Get the global reranker instance."""
    global _reranker
    if _reranker is None:
        _reranker = Reranker()
    return _reranker
