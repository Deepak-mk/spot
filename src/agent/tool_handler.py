"""
Tool handler for the Agentic Analytics Platform.
Executes analytics tools: SQL queries, metadata lookup, semantic search.
"""

import json
import time
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Callable
from pathlib import Path
from enum import Enum

from src.utils.config import get_settings
from src.utils.helpers import duration_ms, ErrorCategory, PlatformError
from src.retrieval.vector_store import get_vector_store, SearchResult
from src.observability.telemetry import get_telemetry
from src.observability.tracing import TraceEventType
from src.observability.latency import OperationType


class ToolType(Enum):
    """Available tool types."""
    SQL_QUERY = "sql_query"
    METADATA_LOOKUP = "metadata_lookup"
    SEMANTIC_SEARCH = "semantic_search"
    CALCULATE = "calculate"


@dataclass
class ToolCall:
    """A tool call request."""
    tool_type: ToolType
    parameters: Dict[str, Any]
    trace_id: Optional[str] = None


@dataclass
class ToolResult:
    """Result from a tool execution."""
    tool_type: ToolType
    success: bool
    result: Any
    duration_ms: float
    error: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "tool_type": self.tool_type.value,
            "success": self.success,
            "result": self.result if self.success else None,
            "error": self.error,
            "duration_ms": round(self.duration_ms, 2),
        }


class SQLQueryTool:
    """
    Executes SQL queries against the semantic data.
    Uses DuckDB or pandas for query execution.
    """
    
    def __init__(self, data_dir: Optional[str] = None):
        settings = get_settings()
        self._data_dir = Path(data_dir or settings.data.semantic_data_dir)
        self._tables_loaded = False
        self._dataframes: Dict[str, Any] = {}
    
    def _load_tables(self):
        """Load CSV files into memory."""
        if self._tables_loaded:
            return
        
        try:
            import pandas as pd
            
            csv_files = [
                ("fact_sales_forecast", "fact_sales_forecast.csv"),
                ("dim_date", "dim_date.csv"),
                ("dim_product", "dim_product.csv"),
                ("dim_store", "dim_store.csv"),
            ]
            
            for table_name, filename in csv_files:
                filepath = self._data_dir / filename
                if filepath.exists():
                    self._dataframes[table_name] = pd.read_csv(filepath)
            
            self._tables_loaded = True
        except ImportError:
            # Pandas not available, queries will fail gracefully
            pass
    
    def execute(self, query: str) -> Dict[str, Any]:
        """
        Execute a SQL query.
        
        Args:
            query: SQL query string
        
        Returns:
            Dict with columns and rows
        """
        self._load_tables()
        
        if not self._dataframes:
            return {"error": "No data tables loaded", "columns": [], "rows": []}
        
        try:
            import duckdb
            
            # Register DataFrames with DuckDB
            conn = duckdb.connect(":memory:")
            for table_name, df in self._dataframes.items():
                conn.register(table_name, df)
            
            # Execute query
            result = conn.execute(query).fetchdf()
            
            return {
                "columns": list(result.columns),
                "rows": result.values.tolist(),
                "row_count": len(result),
            }
        except ImportError:
            # DuckDB not available, try pandas query
            return self._pandas_query(query)
        except Exception as e:
            return {"error": str(e), "columns": [], "rows": []}
    
    def _pandas_query(self, query: str) -> Dict[str, Any]:
        """Fallback query using pandas."""
        # Simple query parsing for basic SELECT statements
        query_lower = query.lower().strip()
        
        if "from fact_sales_forecast" in query_lower:
            df = self._dataframes.get("fact_sales_forecast")
            if df is not None:
                # Very basic aggregation support
                if "sum(revenue)" in query_lower:
                    total = df["revenue"].sum()
                    return {"columns": ["total_revenue"], "rows": [[total]], "row_count": 1}
                elif "count(*)" in query_lower:
                    count = len(df)
                    return {"columns": ["count"], "rows": [[count]], "row_count": 1}
                else:
                    # Return sample
                    sample = df.head(10)
                    return {
                        "columns": list(sample.columns),
                        "rows": sample.values.tolist(),
                        "row_count": len(sample),
                    }
        
        return {"error": "Query not supported without DuckDB", "columns": [], "rows": []}


class MetadataLookupTool:
    """Looks up metadata definitions."""
    
    def __init__(self, metadata_path: Optional[str] = None):
        settings = get_settings()
        data_dir = Path(settings.data.semantic_data_dir)
        self._metadata_path = Path(metadata_path) if metadata_path else data_dir / "metadata.json"
        self._metadata: Optional[Dict] = None
    
    def _load_metadata(self):
        """Load metadata from file."""
        if self._metadata is None:
            with open(self._metadata_path, 'r') as f:
                self._metadata = json.load(f)
    
    def lookup_table(self, table_name: str) -> Optional[Dict]:
        """Look up table definition."""
        self._load_metadata()
        return self._metadata.get("tables", {}).get(table_name)
    
    def lookup_column(self, table_name: str, column_name: str) -> Optional[Dict]:
        """Look up column definition."""
        table = self.lookup_table(table_name)
        if table:
            return table.get("columns", {}).get(column_name)
        return None
    
    def lookup_metric(self, metric_name: str) -> Optional[Dict]:
        """Look up metric definition."""
        self._load_metadata()
        return self._metadata.get("metrics", {}).get(metric_name)
    
    def list_tables(self) -> List[str]:
        """List all table names."""
        self._load_metadata()
        return list(self._metadata.get("tables", {}).keys())
    
    def list_metrics(self) -> List[str]:
        """List all metric names."""
        self._load_metadata()
        return list(self._metadata.get("metrics", {}).keys())
    
    def execute(self, lookup_type: str, name: str, parent: Optional[str] = None) -> Dict:
        """
        Execute a metadata lookup.
        
        Args:
            lookup_type: "table", "column", "metric"
            name: Name to look up
            parent: Parent name (for columns, the table name)
        
        Returns:
            Lookup result
        """
        if lookup_type == "table":
            result = self.lookup_table(name)
        elif lookup_type == "column" and parent:
            result = self.lookup_column(parent, name)
        elif lookup_type == "metric":
            result = self.lookup_metric(name)
        elif lookup_type == "list_tables":
            result = self.list_tables()
        elif lookup_type == "list_metrics":
            result = self.list_metrics()
        else:
            result = None
        
        if result is None:
            return {"found": False, "name": name}
        return {"found": True, "name": name, "definition": result}


class SemanticSearchTool:
    """Semantic search over metadata and schema."""
    
    def __init__(self):
        self._vector_store = get_vector_store()
    
    def execute(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        Execute semantic search.
        
        Args:
            query: Search query
            top_k: Number of results
        
        Returns:
            List of search results
        """
        results = self._vector_store.search(query, top_k=top_k)
        return [r.to_dict() for r in results]


class ToolHandler:
    """
    Central handler for all agent tools.
    Routes tool calls to appropriate executors with observability.
    """
    
    def __init__(self):
        self._sql_tool = SQLQueryTool()
        self._metadata_tool = MetadataLookupTool()
        self._search_tool = SemanticSearchTool()
        self._telemetry = get_telemetry()
    
    def execute(self, tool_call: ToolCall) -> ToolResult:
        """
        Execute a tool call.
        
        Args:
            tool_call: ToolCall with type and parameters
        
        Returns:
            ToolResult with outcome
        """
        start_time = time.perf_counter()
        
        # Log start
        if tool_call.trace_id:
            self._telemetry.add_trace_event(
                trace_id=tool_call.trace_id,
                event_type=TraceEventType.TOOL_CALL_START,
                action=f"Executing tool: {tool_call.tool_type.value}",
                input_data=tool_call.parameters
            )
        
        try:
            result = self._route_tool(tool_call)
            elapsed = duration_ms(start_time)
            
            # Log success
            if tool_call.trace_id:
                self._telemetry.add_trace_event(
                    trace_id=tool_call.trace_id,
                    event_type=TraceEventType.TOOL_CALL_END,
                    action=f"Tool completed: {tool_call.tool_type.value}",
                    duration_ms=elapsed,
                    output_data={"result_type": type(result).__name__}
                )
            
            return ToolResult(
                tool_type=tool_call.tool_type,
                success=True,
                result=result,
                duration_ms=elapsed
            )
            
        except Exception as e:
            elapsed = duration_ms(start_time)
            error_msg = str(e)
            
            # Log error
            if tool_call.trace_id:
                self._telemetry.add_trace_event(
                    trace_id=tool_call.trace_id,
                    event_type=TraceEventType.ERROR_OCCURRED,
                    action=f"Tool failed: {tool_call.tool_type.value}",
                    duration_ms=elapsed,
                    success=False,
                    error_message=error_msg
                )
            
            return ToolResult(
                tool_type=tool_call.tool_type,
                success=False,
                result=None,
                duration_ms=elapsed,
                error=error_msg
            )
    
    def _route_tool(self, tool_call: ToolCall) -> Any:
        """Route tool call to appropriate executor."""
        if tool_call.tool_type == ToolType.SQL_QUERY:
            query = tool_call.parameters.get("query", "")
            return self._sql_tool.execute(query)
        
        elif tool_call.tool_type == ToolType.METADATA_LOOKUP:
            lookup_type = tool_call.parameters.get("lookup_type", "")
            name = tool_call.parameters.get("name", "")
            parent = tool_call.parameters.get("parent")
            return self._metadata_tool.execute(lookup_type, name, parent)
        
        elif tool_call.tool_type == ToolType.SEMANTIC_SEARCH:
            query = tool_call.parameters.get("query", "")
            top_k = tool_call.parameters.get("top_k", 5)
            return self._search_tool.execute(query, top_k)
        
        elif tool_call.tool_type == ToolType.CALCULATE:
            expression = tool_call.parameters.get("expression", "")
            # Safe evaluation for simple math
            try:
                result = eval(expression, {"__builtins__": {}}, {})
                return {"expression": expression, "result": result}
            except Exception as e:
                return {"expression": expression, "error": str(e)}
        
        else:
            raise ValueError(f"Unknown tool type: {tool_call.tool_type}")
    
    def execute_sql(self, query: str, trace_id: Optional[str] = None) -> ToolResult:
        """Convenience method for SQL queries."""
        return self.execute(ToolCall(
            tool_type=ToolType.SQL_QUERY,
            parameters={"query": query},
            trace_id=trace_id
        ))
    
    def execute_search(self, query: str, top_k: int = 5, 
                       trace_id: Optional[str] = None) -> ToolResult:
        """Convenience method for semantic search."""
        return self.execute(ToolCall(
            tool_type=ToolType.SEMANTIC_SEARCH,
            parameters={"query": query, "top_k": top_k},
            trace_id=trace_id
        ))


# Singleton instance
_tool_handler: Optional[ToolHandler] = None


def get_tool_handler() -> ToolHandler:
    """Get the global tool handler instance."""
    global _tool_handler
    if _tool_handler is None:
        _tool_handler = ToolHandler()
    return _tool_handler
