
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.abspath("."))

from src.agent.sql_executor import get_sql_executor

def test_dashboard_queries():
    print("Initializing SQL Executor...")
    sql = get_sql_executor()
    
    # Test 1: Simple Aggregation (Metrics)
    print("\nTest 1: Total Revenue Metric")
    query1 = "SELECT SUM(revenue) as val FROM fact_sales_forecast"
    result1 = sql.execute(query1)
    if result1.success:
        print(f"✅ Success: {result1.rows}")
    else:
        print(f"❌ Failed: {result1.error}")

    # Test 2: Group By (Charts)
    print("\nTest 2: Revenue by Region Chart")
    query2 = """
        SELECT s.region, SUM(f.revenue) as revenue
        FROM fact_sales_forecast f
        JOIN dim_store s ON f.store_id = s.store_id
        GROUP BY s.region ORDER BY revenue DESC
    """
    result2 = sql.execute(query2)
    if result2.success:
        print(f"✅ Success: {len(result2.rows)} rows returned")
    else:
        print(f"❌ Failed: {result2.error}")
        
    print("\nchecking data dir:")
    from src.utils.config import get_settings
    settings = get_settings()
    print(f"Semantic Data Dir: {settings.semantic_data_dir}")
    print(f"Exists? {Path(settings.semantic_data_dir).exists()}")
    import os
    if Path(settings.semantic_data_dir).exists():
        print(f"Files: {os.listdir(settings.semantic_data_dir)}")

if __name__ == "__main__":
    test_dashboard_queries()
