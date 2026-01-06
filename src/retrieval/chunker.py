"""
Document chunking for the Agentic Analytics Platform.
Splits metadata and schema into chunks for embedding.
"""

import json
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from pathlib import Path

from src.utils.helpers import generate_trace_id


@dataclass
class Chunk:
    """A chunk of text for embedding."""
    chunk_id: str
    content: str
    source: str
    chunk_type: str  # "table", "column", "metric", "relationship", "query"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "chunk_id": self.chunk_id,
            "content": self.content,
            "source": self.source,
            "chunk_type": self.chunk_type,
            "metadata": self.metadata,
        }


class MetadataChunker:
    """
    Chunks semantic metadata into embeddable units.
    Each chunk captures a meaningful piece of schema or business context.
    """
    
    def __init__(self, include_examples: bool = True):
        self._include_examples = include_examples
    
    def chunk_metadata(self, metadata: dict) -> List[Chunk]:
        """
        Chunk metadata.json into embeddable pieces.
        
        Chunking strategy:
        - One chunk per table (summary)
        - One chunk per column (with table context)
        - One chunk per metric definition
        - One chunk per relationship
        - One chunk per sample query
        """
        chunks = []
        
        # Chunk tables and columns
        tables = metadata.get("tables", {})
        for table_name, table_info in tables.items():
            # Table-level chunk
            table_chunk = self._chunk_table(table_name, table_info)
            chunks.append(table_chunk)
            
            # Column-level chunks
            columns = table_info.get("columns", {})
            for col_name, col_info in columns.items():
                col_chunk = self._chunk_column(table_name, col_name, col_info)
                chunks.append(col_chunk)
        
        # Chunk metrics
        metrics = metadata.get("metrics", {})
        for metric_name, metric_info in metrics.items():
            metric_chunk = self._chunk_metric(metric_name, metric_info)
            chunks.append(metric_chunk)
        
        # Chunk relationships
        relationships = metadata.get("relationships", [])
        for i, rel in enumerate(relationships):
            rel_chunk = self._chunk_relationship(i, rel)
            chunks.append(rel_chunk)
        
        # Chunk sample queries
        if self._include_examples:
            sample_queries = metadata.get("sample_queries", [])
            for i, query in enumerate(sample_queries):
                query_chunk = self._chunk_sample_query(i, query)
                chunks.append(query_chunk)
        
        return chunks
    
    def _chunk_table(self, table_name: str, table_info: dict) -> Chunk:
        """Create a chunk for a table."""
        description = table_info.get("description", "")
        primary_key = table_info.get("primary_key", "")
        grain = table_info.get("grain", "")
        
        columns = table_info.get("columns", {})
        column_list = ", ".join(columns.keys())
        
        content = f"Table: {table_name}\n"
        content += f"Description: {description}\n"
        if primary_key:
            content += f"Primary Key: {primary_key}\n"
        if grain:
            content += f"Grain: {grain}\n"
        content += f"Columns: {column_list}"
        
        return Chunk(
            chunk_id=f"table_{table_name}",
            content=content,
            source="metadata.json",
            chunk_type="table",
            metadata={"table_name": table_name, "column_count": len(columns)}
        )
    
    def _chunk_column(self, table_name: str, col_name: str, col_info: dict) -> Chunk:
        """Create a chunk for a column."""
        col_type = col_info.get("type", "")
        description = col_info.get("description", "")
        business_name = col_info.get("business_name", col_name)
        aggregation = col_info.get("aggregation", "")
        foreign_key = col_info.get("foreign_key", "")
        
        content = f"Column: {table_name}.{col_name}\n"
        content += f"Business Name: {business_name}\n"
        content += f"Type: {col_type}\n"
        content += f"Description: {description}"
        if aggregation:
            content += f"\nDefault Aggregation: {aggregation}"
        if foreign_key:
            content += f"\nForeign Key to: {foreign_key}"
        
        sample_values = col_info.get("sample_values", [])
        if sample_values:
            content += f"\nSample Values: {', '.join(str(v) for v in sample_values)}"
        
        return Chunk(
            chunk_id=f"column_{table_name}_{col_name}",
            content=content,
            source="metadata.json",
            chunk_type="column",
            metadata={
                "table_name": table_name,
                "column_name": col_name,
                "column_type": col_type,
                "is_foreign_key": bool(foreign_key)
            }
        )
    
    def _chunk_metric(self, metric_name: str, metric_info: dict) -> Chunk:
        """Create a chunk for a metric definition."""
        description = metric_info.get("description", "")
        formula = metric_info.get("formula", "")
        format_type = metric_info.get("format", "")
        
        content = f"Metric: {metric_name}\n"
        content += f"Description: {description}\n"
        content += f"Formula: {formula}"
        if format_type:
            content += f"\nFormat: {format_type}"
        
        return Chunk(
            chunk_id=f"metric_{metric_name}",
            content=content,
            source="metadata.json",
            chunk_type="metric",
            metadata={"metric_name": metric_name, "formula": formula}
        )
    
    def _chunk_relationship(self, index: int, rel: dict) -> Chunk:
        """Create a chunk for a relationship."""
        from_table = rel.get("from_table", "")
        from_column = rel.get("from_column", "")
        to_table = rel.get("to_table", "")
        to_column = rel.get("to_column", "")
        rel_type = rel.get("type", "")
        
        content = f"Relationship: {from_table}.{from_column} -> {to_table}.{to_column}\n"
        content += f"Type: {rel_type}\n"
        content += f"The {from_table} table references {to_table} through the {from_column} column."
        
        return Chunk(
            chunk_id=f"relationship_{index}",
            content=content,
            source="metadata.json",
            chunk_type="relationship",
            metadata={"from_table": from_table, "to_table": to_table}
        )
    
    def _chunk_sample_query(self, index: int, query: str) -> Chunk:
        """Create a chunk for a sample query."""
        content = f"Sample Question: {query}\n"
        content += "This is an example of a question that can be answered using the sales and forecast dataset."
        
        return Chunk(
            chunk_id=f"sample_query_{index}",
            content=content,
            source="metadata.json",
            chunk_type="query",
            metadata={"query_text": query}
        )


def chunk_metadata_file(metadata_path: str) -> List[Chunk]:
    """
    Load and chunk a metadata.json file.
    
    Args:
        metadata_path: Path to metadata.json
    
    Returns:
        List of Chunk objects
    """
    with open(metadata_path, 'r') as f:
        metadata = json.load(f)
    
    chunker = MetadataChunker()
    return chunker.chunk_metadata(metadata)


def chunks_to_documents(chunks: List[Chunk]) -> List[Dict]:
    """Convert chunks to document format for vector store."""
    return [
        {
            "id": chunk.chunk_id,
            "content": chunk.content,
            "metadata": {
                "source": chunk.source,
                "chunk_type": chunk.chunk_type,
                **chunk.metadata
            }
        }
        for chunk in chunks
    ]
