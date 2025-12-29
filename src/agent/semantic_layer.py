"""
Semantic Layer Abstraction.
Decouples the Agent from the raw Metadata Store.
Currently backed by metadata.json, but designed to swap for Cube.js / dbt Semantic Layer.
"""

import json
from dataclasses import dataclass
from typing import List, Optional, Dict
from pathlib import Path

from src.utils.config import get_settings

@dataclass
class MetricDefinition:
    name: str
    description: str
    formula: str
    format: str

@dataclass
class DimensionDefinition:
    name: str
    table: str
    column: str
    description: str

class SemanticLayer:
    """
    The Semantic Layer acts as the single source of truth for business logic.
    It translates business terms (Revenue, Churn) into data definitions.
    """
    
    def __init__(self, metadata_path: str = "data/metadata.json"):
        self._path = metadata_path
        self._metrics: Dict[str, MetricDefinition] = {}
        self._dimensions: Dict[str, DimensionDefinition] = {}
        self._loaded = False
        
    def _load(self):
        if self._loaded:
            return
            
        try:
            with open(self._path, 'r') as f:
                data = json.load(f)
                
            # Parse Metrics
            for m_name, m_info in data.get("metrics", {}).items():
                self._metrics[m_name] = MetricDefinition(
                    name=m_name,
                    description=m_info.get("description", ""),
                    formula=m_info.get("formula", ""),
                    format=m_info.get("format", "")
                )
                
            # Parse Dimensions (from tables)
            for t_name, t_info in data.get("tables", {}).items():
                for c_name, c_info in t_info.get("columns", {}).items():
                    # Check if it's a dimension
                    if c_info.get("type") in ["TEXT", "DATE", "VARCHAR"]:
                        full_name = f"{t_name}.{c_name}"
                        self._dimensions[full_name] = DimensionDefinition(
                            name=c_info.get("business_name", c_name),
                            table=t_name,
                            column=c_name,
                            description=c_info.get("description", "")
                        )
            
            self._loaded = True
        except Exception as e:
            print(f"Error loading semantic layer: {e}")

    def list_metrics(self) -> List[MetricDefinition]:
        self._load()
        return list(self._metrics.values())

    def get_metric(self, name: str) -> Optional[MetricDefinition]:
        self._load()
        return self._metrics.get(name)

    def get_context_block(self) -> str:
        """Returns a consolidated business context block for the LLM."""
        self._load()
        
        lines = ["## Business Logic (Semantic Layer)"]
        
        lines.append("\n### Key Metrics")
        for m in self._metrics.values():
            lines.append(f"- **{m.name}**: {m.description} (Formula: `{m.formula}`)")
            
        return "\n".join(lines)

# Singleton
_semantic_layer = None

def get_semantic_layer() -> SemanticLayer:
    global _semantic_layer
    if _semantic_layer is None:
        _semantic_layer = SemanticLayer()
    return _semantic_layer
