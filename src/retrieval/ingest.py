"""
Ingestion pipeline for the Agentic Analytics Platform.
Loads semantic data and metadata, generates embeddings, and stores in vector DB.
"""

import json
import time
from pathlib import Path
from typing import Optional, Dict, List
from dataclasses import dataclass

from src.utils.config import get_settings
from src.utils.helpers import timestamp_now, duration_ms
from src.retrieval.chunker import chunk_metadata_file, chunks_to_documents, Chunk
from src.retrieval.embeddings import get_embedding_model
from src.retrieval.vector_store import get_vector_store, VectorStore
from src.observability.telemetry import get_telemetry
from src.observability.tracing import TraceEventType


@dataclass
class IngestionResult:
    """Result of an ingestion operation."""
    success: bool
    documents_ingested: int
    chunks_created: int
    embedding_time_ms: float
    total_time_ms: float
    errors: List[str]
    
    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "documents_ingested": self.documents_ingested,
            "chunks_created": self.chunks_created,
            "embedding_time_ms": round(self.embedding_time_ms, 2),
            "total_time_ms": round(self.total_time_ms, 2),
            "errors": self.errors,
        }


class SemanticDataIngestor:
    """
    Ingests semantic data (metadata, schema) into the vector store.
    Handles chunking, embedding, and storage.
    """
    
    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        data_dir: Optional[str] = None
    ):
        settings = get_settings()
        self._vector_store = vector_store or get_vector_store()
        self._data_dir = Path(data_dir or settings.semantic_data_dir)
        self._embedding_model = get_embedding_model()
        self._telemetry = get_telemetry()
    
    def ingest_metadata(
        self,
        metadata_path: Optional[str] = None,
        trace_id: Optional[str] = None,
        clear_existing: bool = True
    ) -> IngestionResult:
        """
        Ingest metadata.json into the vector store.
        
        Args:
            metadata_path: Path to metadata.json (uses default if not provided)
            trace_id: Optional trace ID for observability
            clear_existing: Whether to clear existing documents first
        
        Returns:
            IngestionResult with details
        """
        start_time = time.perf_counter()
        errors = []
        
        # Determine metadata path
        if metadata_path:
            meta_path = Path(metadata_path)
        else:
            meta_path = self._data_dir / "metadata.json"
        
        # Add trace event
        if trace_id:
            self._telemetry.add_trace_event(
                trace_id=trace_id,
                event_type=TraceEventType.RETRIEVAL_START,
                action="Starting metadata ingestion",
                input_data={"metadata_path": str(meta_path)}
            )
        
        try:
            # Load and chunk metadata
            chunks = chunk_metadata_file(str(meta_path))
            documents = chunks_to_documents(chunks)
            
            # Clear existing if requested
            if clear_existing:
                self._vector_store.clear()
            
            # Add documents (this also generates embeddings)
            embedding_start = time.perf_counter()
            doc_count = self._vector_store.add_documents(documents, trace_id)
            embedding_time = duration_ms(embedding_start)
            
            total_time = duration_ms(start_time)
            
            # Add success trace event
            if trace_id:
                self._telemetry.add_trace_event(
                    trace_id=trace_id,
                    event_type=TraceEventType.RETRIEVAL_END,
                    action="Metadata ingestion complete",
                    duration_ms=total_time,
                    output_data={
                        "chunks": len(chunks),
                        "documents": doc_count
                    }
                )
            
            return IngestionResult(
                success=True,
                documents_ingested=doc_count,
                chunks_created=len(chunks),
                embedding_time_ms=embedding_time,
                total_time_ms=total_time,
                errors=[]
            )
            
        except Exception as e:
            error_msg = f"Ingestion failed: {str(e)}"
            errors.append(error_msg)
            
            if trace_id:
                self._telemetry.add_trace_event(
                    trace_id=trace_id,
                    event_type=TraceEventType.ERROR_OCCURRED,
                    action="Metadata ingestion failed",
                    success=False,
                    error_message=error_msg
                )
            
            return IngestionResult(
                success=False,
                documents_ingested=0,
                chunks_created=0,
                embedding_time_ms=0,
                total_time_ms=duration_ms(start_time),
                errors=errors
            )
    
    def ingest_custom_documents(
        self,
        documents: List[Dict],
        trace_id: Optional[str] = None
    ) -> IngestionResult:
        """
        Ingest custom documents directly.
        
        Args:
            documents: List of dicts with 'id', 'content', 'metadata'
            trace_id: Optional trace ID
        
        Returns:
            IngestionResult
        """
        start_time = time.perf_counter()
        
        try:
            embedding_start = time.perf_counter()
            doc_count = self._vector_store.add_documents(documents, trace_id)
            embedding_time = duration_ms(embedding_start)
            
            return IngestionResult(
                success=True,
                documents_ingested=doc_count,
                chunks_created=doc_count,
                embedding_time_ms=embedding_time,
                total_time_ms=duration_ms(start_time),
                errors=[]
            )
        except Exception as e:
            return IngestionResult(
                success=False,
                documents_ingested=0,
                chunks_created=0,
                embedding_time_ms=0,
                total_time_ms=duration_ms(start_time),
                errors=[str(e)]
            )
    
    def refresh_embeddings(self, trace_id: Optional[str] = None) -> IngestionResult:
        """
        Refresh all embeddings by re-ingesting metadata.
        Called periodically or when data changes.
        """
        return self.ingest_metadata(trace_id=trace_id, clear_existing=True)
    
    def get_ingestion_status(self) -> Dict:
        """Get current ingestion status."""
        return {
            "vector_store_count": self._vector_store.count(),
            "embedding_model": self._embedding_model.model_name,
            "embedding_dimension": self._embedding_model.dimension,
            "data_dir": str(self._data_dir),
        }


def ingest_semantic_data(
    metadata_path: Optional[str] = None,
    trace_id: Optional[str] = None
) -> IngestionResult:
    """
    Convenience function to ingest semantic data.
    
    Args:
        metadata_path: Optional path to metadata.json
        trace_id: Optional trace ID
    
    Returns:
        IngestionResult
    """
    ingestor = SemanticDataIngestor()
    return ingestor.ingest_metadata(metadata_path, trace_id)


def refresh_embeddings(trace_id: Optional[str] = None) -> IngestionResult:
    """Convenience function to refresh all embeddings."""
    ingestor = SemanticDataIngestor()
    return ingestor.refresh_embeddings(trace_id)
