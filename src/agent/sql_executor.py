"""
SQL Executor for the Agentic Analytics Platform.
Executes real SQL queries against the semantic data using DuckDB.
"""

import json
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple
from pathlib import Path
import time

from src.utils.config import get_settings
from src.utils.helpers import duration_ms


@dataclass
class QueryResult:
    """Result from SQL query execution."""
    success: bool
    columns: List[str] = field(default_factory=list)
    rows: List[List[Any]] = field(default_factory=list)
    row_count: int = 0
    duration_ms: float = 0.0
    query: str = ""
    error: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "columns": self.columns,
            "rows": self.rows[:10],  # Limit for display
            "row_count": self.row_count,
            "duration_ms": round(self.duration_ms, 2),
            "error": self.error,
        }
    
    def to_markdown_table(self, max_rows: int = 10) -> str:
        """Convert result to markdown table."""
        if not self.success or not self.columns:
            return f"Error: {self.error}" if self.error else "No data"
        
        # Header
        header = "| " + " | ".join(str(c) for c in self.columns) + " |"
        separator = "| " + " | ".join("---" for _ in self.columns) + " |"
        
        # Rows
        rows_md = []
        for row in self.rows[:max_rows]:
            row_str = "| " + " | ".join(self._format_cell(c) for c in row) + " |"
            rows_md.append(row_str)
        
        table = "\n".join([header, separator] + rows_md)
        
        if self.row_count > max_rows:
            table += f"\n\n*Showing {max_rows} of {self.row_count} rows*"
        
        return table
    
    def _format_cell(self, value: Any) -> str:
        """Format cell value for display."""
        if value is None:
            return "NULL"
        if isinstance(value, float):
            return f"{value:,.2f}"
        if isinstance(value, int):
            return f"{value:,}"
        return str(value)


class SQLExecutor:
    """
    Executes SQL queries against the semantic data.
    Uses DuckDB for efficient analytics queries.
    """
    
    def __init__(self, data_dir: Optional[str] = None):
        settings = get_settings()
        self._data_dir = Path(data_dir or settings.data.semantic_data_dir)
        self._conn = None
        self._initialized = False
    
    def _initialize(self):
        """Initialize DuckDB connection and load data."""
        if self._initialized:
            return
        
        try:
            import duckdb
            import pandas as pd
            
            self._conn = duckdb.connect(":memory:")
            
            # Load all CSV files as tables
            csv_files = {
                "fact_sales_forecast": "fact_sales_forecast.csv",
                "dim_date": "dim_date.csv",
                "dim_product": "dim_product.csv",
                "dim_store": "dim_store.csv",
            }
            
            for table_name, filename in csv_files.items():
                filepath = self._data_dir / filename
                if filepath.exists():
                    df = pd.read_csv(filepath)
                    self._conn.register(table_name, df)
                    print(f"Loaded {table_name}: {len(df)} rows")
            
            self._initialized = True
            
        except ImportError as e:
            print(f"Warning: Could not import duckdb or pandas: {e}")
            self._initialized = False
    
    def execute(self, query: str) -> QueryResult:
        """
        Execute a SQL query and return results.
        
        Args:
            query: SQL query string
        
        Returns:
            QueryResult with data or error
        """
        self._initialize()
        
        if not self._conn:
            return QueryResult(
                success=False,
                query=query,
                error="Database not initialized. Install duckdb and pandas."
            )
        
        start_time = time.perf_counter()
        
        try:
            # Execute query
            result = self._conn.execute(query)
            df = result.fetchdf()
            
            elapsed = duration_ms(start_time)
            
            return QueryResult(
                success=True,
                columns=list(df.columns),
                rows=df.values.tolist(),
                row_count=len(df),
                duration_ms=elapsed,
                query=query
            )
            
        except Exception as e:
            elapsed = duration_ms(start_time)
            return QueryResult(
                success=False,
                query=query,
                duration_ms=elapsed,
                error=str(e)
            )
    
    def get_schema(self) -> Dict[str, List[str]]:
        """Get schema of all tables."""
        self._initialize()
        
        if not self._conn:
            return {}
        
        schema = {}
        tables = ["fact_sales_forecast", "dim_date", "dim_product", "dim_store"]
        
        for table in tables:
            try:
                result = self._conn.execute(f"DESCRIBE {table}").fetchdf()
                schema[table] = list(result["column_name"])
            except:
                pass
        
        return schema
    
    def get_sample_data(self, table: str, limit: int = 5) -> QueryResult:
        """Get sample data from a table."""
        return self.execute(f"SELECT * FROM {table} LIMIT {limit}")
    
    def get_aggregations(self) -> Dict[str, Any]:
        """Get common aggregations for quick insights."""
        self._initialize()
        
        if not self._conn:
            return {}
        
        aggregations = {}
        
        # Revenue by region
        try:
            result = self.execute("""
                SELECT s.region, 
                       SUM(f.revenue) as total_revenue,
                       SUM(f.units_sold) as total_units,
                       COUNT(*) as transactions
                FROM fact_sales_forecast f
                JOIN dim_store s ON f.store_id = s.store_id
                GROUP BY s.region
                ORDER BY total_revenue DESC
            """)
            if result.success:
                aggregations["revenue_by_region"] = result.to_dict()
        except:
            pass
        
        # Revenue by category
        try:
            result = self.execute("""
                SELECT p.category,
                       SUM(f.revenue) as total_revenue,
                       AVG(f.revenue) as avg_revenue
                FROM fact_sales_forecast f
                JOIN dim_product p ON f.product_id = p.product_id
                GROUP BY p.category
                ORDER BY total_revenue DESC
            """)
            if result.success:
                aggregations["revenue_by_category"] = result.to_dict()
        except:
            pass
        
        # Monthly trend
        try:
            result = self.execute("""
                SELECT d.month, d.month_name,
                       SUM(f.revenue) as total_revenue,
                       SUM(f.actual_sales) as actual_sales,
                       SUM(f.forecast_sales) as forecast_sales
                FROM fact_sales_forecast f
                JOIN dim_date d ON f.date_id = d.date_id
                GROUP BY d.month, d.month_name
                ORDER BY d.month
            """)
            if result.success:
                aggregations["monthly_trend"] = result.to_dict()
        except:
            pass
        
        return aggregations


# Singleton instance
_sql_executor: Optional[SQLExecutor] = None


def get_sql_executor() -> SQLExecutor:
    """Get the global SQL executor instance."""
    global _sql_executor
    if _sql_executor is None:
        _sql_executor = SQLExecutor()
    return _sql_executor
