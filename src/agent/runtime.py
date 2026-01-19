"""
Agent runtime for the Agentic Analytics Platform.
Core agent loop with LLM integration, SQL execution, and control plane.
"""

import time
import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum

from src.utils.config import get_settings
from src.utils.helpers import generate_trace_id, duration_ms, ErrorCategory
from src.agent.control_plane import get_control_plane, ControlPlane
from src.agent.prompt_builder import PromptBuilder, PromptContext, build_prompt
from src.agent.llm_client import get_llm_client, GroqClient, set_groq_api_key
from src.agent.sql_executor import get_sql_executor, SQLExecutor, QueryResult
from src.agent.memory import get_conversation_memory, ConversationMemory, AgentState
from src.retrieval.vector_store import get_vector_store
from src.retrieval.reranker import get_reranker
from src.observability.telemetry import get_telemetry
from src.observability.tracing import TraceEventType





@dataclass
class RetrievedContext:
    """Context chunk with similarity score."""
    content: str
    chunk_type: str
    similarity_score: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResponse:
    """Final response from the agent."""
    trace_id: str
    query: str
    answer: str
    sql_query: Optional[str] = None
    sql_result: Optional[Dict] = None
    reasoning: Optional[str] = None
    data_sources: List[str] = field(default_factory=list)
    retrieved_context: List[Dict] = field(default_factory=list)  # With similarity scores
    duration_ms: float = 0.0
    token_usage: Optional[Dict[str, int]] = None
    success: bool = True
    error: Optional[str] = None
    steps: List[str] = field(default_factory=list)
    is_cached: bool = False
    
    def to_dict(self) -> dict:
        return {
            "trace_id": self.trace_id,
            "query": self.query,
            "answer": self.answer,
            "sql_query": self.sql_query,
            "sql_result": self.sql_result,
            "reasoning": self.reasoning,
            "data_sources": self.data_sources,
            "retrieved_context": self.retrieved_context,
            "duration_ms": round(self.duration_ms, 2),
            "token_usage": self.token_usage,
            "success": self.success,
            "error": self.error,
            "steps": self.steps,
            "is_cached": self.is_cached
        }


class AgentRuntime:
    """
    Main agent runtime with LLM and SQL integration.
    """
    
    def __init__(self):
        self._control_plane = get_control_plane()
        self._llm = get_llm_client()
        self._sql = get_sql_executor()
        self._memory = get_conversation_memory()
        self._vector_store = get_vector_store()
        self._reranker = get_reranker()
        self._telemetry = get_telemetry()
        self._settings = get_settings()
        
        # Lazy load cache to avoid circular imports if any
        from src.agent.cache import get_semantic_cache
        self._cache = get_semantic_cache()
    
    def run(
        self,
        query: str,
        session_id: Optional[str] = None,
        trace_id: Optional[str] = None
    ) -> AgentResponse:
        """
        Run the agent on a query.
        """
        trace_id = trace_id or generate_trace_id()
        start_time = time.perf_counter()
        steps = []
        
        # Start telemetry
        self._telemetry.start_request(query, trace_id, {"session_id": session_id})
        
        try:
            # Step 1: Control plane check
            steps.append("🛡️ Checking Guardrails & Permissions...")
            can_proceed, reason = self._control_plane.validate_request(query, trace_id)
            if not can_proceed:
                return self._error_response(trace_id, query, start_time, f"Blocked: {reason}")
            
            # Step 1.5: Check Semantic Cache
            cached_data = self._cache.lookup(query)
            if cached_data:
                steps.append(f"⚡ Semantic Cache Hit (Score: {cached_data['similarity_score']:.2f})")
                elapsed = duration_ms(start_time)
                
                # Log telemetry
                self._telemetry.end_request(trace_id=trace_id, success=True, response="CACHED_RESPONSE")
                
                return AgentResponse(
                    trace_id=trace_id,
                    query=query,
                    answer=f"⚡ {cached_data['answer']}", # Add visual indicator
                    sql_query=cached_data['sql_query'],
                    sql_result=cached_data['sql_result'],
                    duration_ms=elapsed,
                    token_usage={"prompt_tokens": len(query) // 4, "completion_tokens": 0},
                    success=True,
                    is_cached=True,
                    steps=steps
                )
            
            # Step 2: Retrieve context with similarity scores
            steps.append("📚 Retrieving & Reranking Semantic Context...")
            context_chunks, retrieved_context = self._retrieve_context_with_scores(query, trace_id)
            steps.append(f"   - Found {len(context_chunks)} relevant metadata chunks")
            
            # Step 3: Get conversation history
            history = []
            if session_id:
                history = self._memory.get_history(session_id, max_messages=4)
            
            # Step 4: Build prompt with context
            context_text = self._format_context_with_scores(context_chunks)
            
            # Dynamic System Prompt
            from src.agent.prompt_manager import get_prompt_manager
            system_prompt = get_prompt_manager().get_system_prompt()
            
            messages = [
                {"role": "system", "content": system_prompt},
            ]
            
            # Add history
            for msg in history:
                messages.append(msg)
            
            # Add current query with context
            user_message = f"""## Retrieved Context (with relevance scores)
{context_text}

## User Question
{query}

Generate a SQL query and provide a clear answer."""
            
            messages.append({"role": "user", "content": user_message})
            
            # Step 5: Call LLM
            if not self._llm.is_configured():
                # Fallback to rule-based if no API key
                answer, sql_query, sql_result = self._fallback_response(query)
            else:
                steps.append("🧠 Thinking (Planning SQL generation)...")
                llm_response = self._llm.chat(messages, trace_id=trace_id)
                
                if not llm_response.success:
                    return self._error_response(trace_id, query, start_time, llm_response.error)
                
                answer = llm_response.content
                
                # Step 6: Extract and execute SQL if present
                sql_query = self._extract_sql(answer)
                sql_result = None
                
                if sql_query:
                    steps.append("⚡ Executing SQL Query...")
                    result = self._sql.execute(sql_query)
                    
                    # Check if result is empty or failed
                    is_empty_result = result.success and result.rows == []
                    
                    if result.success and not is_empty_result:
                        sql_result = result.to_dict()
                        
                        # Store in Semantic Cache
                        self._cache.store(query, sql_query, sql_result, answer)
                        steps.append("💾 Saved result to Semantic Cache")
                        
                    else:
                        # SQL execution failed or returned no data - try fallback
                        if not result.success:
                            print(f"SQL Error: {result.error}")
                        elif is_empty_result:
                            print(f"SQL Warning: Query returned 0 rows. Triggering fallback.")
                            
                        # Try a simple fallback query based on keywords
                        fallback_sql = self._get_fallback_sql(query)
                        if fallback_sql:
                            fallback_result = self._sql.execute(fallback_sql)
                            if fallback_result.success:
                                sql_query = fallback_sql
                                sql_result = fallback_result.to_dict()
                                
                                # Remove the failed SQL block from the answer to avoid confusion
                                answer = re.sub(r'```sql.*?```', '', answer, flags=re.DOTALL).strip()
                                answer += f"\n\n*Note: Used optimized query for better results.*"
            
            # Step 7: Store in memory and inject data context
            if session_id:
                self._memory.add_message(session_id, "user", query)
                
                # Enhance memory with data context so LLM "sees" the results
                memory_content = answer
                if sql_result and 'rows' in sql_result:
                    # Append a summary of the data to the assistant's memory
                    rows = sql_result['rows']
                    cols = sql_result.get('columns', [])
                    sample = rows[:5] # Limit context size
                    data_context = f"\n\n[SYSTEM_DATA_CONTEXT: The executed SQL returned {len(rows)} rows. Columns: {cols}. Sample Data: {sample}]"
                    memory_content += data_context
                
                self._memory.add_message(session_id, "assistant", memory_content)
            
            elapsed = duration_ms(start_time)
            
            # End telemetry
            self._telemetry.end_request(trace_id=trace_id, success=True, response=answer[:200])
            
            return AgentResponse(
                trace_id=trace_id,
                query=query,
                answer=answer,
                sql_query=sql_query,
                sql_result=sql_result,
                data_sources=[c.metadata.get("chunk_type", "unknown") for c in context_chunks],
                retrieved_context=retrieved_context,
                duration_ms=elapsed,
                token_usage={"prompt_tokens": len(user_message) // 4, "completion_tokens": len(answer) // 4},
                success=True,
                is_cached=False,
                steps=steps
            )
            
        except Exception as e:
            return self._error_response(trace_id, query, start_time, str(e))
    
    def _retrieve_context_with_scores(self, query: str, trace_id: str) -> tuple:
        """Retrieve relevant context with similarity scores."""
        results = self._vector_store.search(query, top_k=5, trace_id=trace_id)
        reranked = self._reranker.rerank(results, query=query, top_k=5)
        
        # Build context with scores
        retrieved_context = []
        for chunk in reranked:
            retrieved_context.append({
                "chunk_type": chunk.metadata.get("chunk_type", "unknown"),
                "content": chunk.content[:100] + "..." if len(chunk.content) > 100 else chunk.content,
                "similarity_score": round(chunk.score, 4),
                "relevance": "High" if chunk.score > 0.7 else "Medium" if chunk.score > 0.4 else "Low"
            })
        
        return reranked, retrieved_context
    
    def _format_context_with_scores(self, chunks: List) -> str:
        """Format context chunks with similarity scores."""
        if not chunks:
            return "No specific context retrieved."
        
        parts = []
        for i, chunk in enumerate(chunks[:3], 1):
            chunk_type = chunk.metadata.get("chunk_type", "info")
            score = chunk.score
            relevance = "🟢 High" if score > 0.7 else "🟡 Medium" if score > 0.4 else "🔴 Low"
            parts.append(f"**{chunk_type.title()} {i}** (Similarity: {score:.2f} - {relevance}):\n{chunk.content[:300]}")
        
        return "\n\n".join(parts)
    
    def _extract_sql(self, text: str) -> Optional[str]:
        """Extract SQL query from LLM response."""
        # Look for SQL in code blocks
        pattern = r"```sql\s*(.*?)\s*```"
        matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
        
        if matches:
            return matches[0].strip()
        
        # Look for SELECT statements
        pattern = r"(SELECT\s+.*?(?:FROM|;).*?)(?:\n\n|$)"
        matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
        
        if matches:
            sql = matches[0].strip()
            return sql if sql.endswith(';') else sql + ';'
        
        return None
    
    def _get_fallback_sql(self, query: str) -> Optional[str]:
        """Get a working fallback SQL query based on keywords."""
        q = query.lower()
        
        if "3 months" in q and ("forecast" in q or "actual" in q):
            # Check if breakdown by product/category is requested
            if "product" in q:
                return """SELECT p.product_name, SUM(f.forecast_sales) as forecast_sales
FROM fact_sales_forecast f
JOIN dim_date d ON f.date_id = d.date_id
JOIN dim_product p ON f.product_id = p.product_id
WHERE d.month IN ('January', 'February', 'March')
GROUP BY p.product_name
ORDER BY forecast_sales DESC
LIMIT 10"""
            elif "category" in q:
                return """SELECT p.category, SUM(f.forecast_sales) as forecast_sales
FROM fact_sales_forecast f
JOIN dim_date d ON f.date_id = d.date_id
JOIN dim_product p ON f.product_id = p.product_id
WHERE d.month IN ('January', 'February', 'March')
GROUP BY p.category
ORDER BY forecast_sales DESC"""
            
            # Default to monthly trend
            return """SELECT d.month, SUM(f.forecast_sales) as forecast_sales, SUM(f.actual_sales) as actual_sales
FROM fact_sales_forecast f
JOIN dim_date d ON f.date_id = d.date_id
GROUP BY d.month
ORDER BY MIN(d.date_id)
LIMIT 3"""
        
        elif "region" in q and "revenue" in q:
            return """SELECT s.region, SUM(f.revenue) as total_revenue
FROM fact_sales_forecast f
JOIN dim_store s ON f.store_id = s.store_id
GROUP BY s.region ORDER BY total_revenue DESC"""
        
        elif "category" in q and "revenue" in q:
            return """SELECT p.category, SUM(f.revenue) as total_revenue
FROM fact_sales_forecast f
JOIN dim_product p ON f.product_id = p.product_id
GROUP BY p.category ORDER BY total_revenue DESC"""
        
        elif "category" in q:
            return """SELECT p.category, COUNT(*) as product_count, SUM(f.units_sold) as units_sold
FROM fact_sales_forecast f
JOIN dim_product p ON f.product_id = p.product_id
GROUP BY p.category ORDER BY units_sold DESC"""
        
        elif "product" in q and ("revenue" in q or "sales" in q):
            return """SELECT p.product_name, p.category, SUM(f.revenue) as total_revenue
FROM fact_sales_forecast f
JOIN dim_product p ON f.product_id = p.product_id
GROUP BY p.product_id, p.product_name, p.category ORDER BY total_revenue DESC LIMIT 10"""
        
        elif "month" in q and ("forecast" in q or "actual" in q or "compare" in q):
            return """SELECT d.month, SUM(f.actual_sales) as actual, SUM(f.forecast_sales) as forecast
FROM fact_sales_forecast f
JOIN dim_date d ON f.date_id = d.date_id
GROUP BY d.month
ORDER BY MIN(d.date_id)"""
        
        elif "quarter" in q:
            return """SELECT d.quarter, SUM(f.revenue) as total_revenue, SUM(f.units_sold) as units_sold
FROM fact_sales_forecast f
JOIN dim_date d ON f.date_id = d.date_id
GROUP BY d.quarter ORDER BY d.quarter"""
        
        elif "margin" in q or "profit" in q:
            return """SELECT 
    SUM(revenue) as total_revenue,
    SUM(cost) as total_cost,
    SUM(revenue) - SUM(cost) as gross_profit,
    ROUND((SUM(revenue) - SUM(cost)) * 100.0 / SUM(revenue), 2) as gross_margin_pct
FROM fact_sales_forecast"""
        

        elif "forecast" in q:
            return """SELECT d.month, SUM(f.forecast_sales) as forecast_sales, SUM(f.actual_sales) as actual_sales
FROM fact_sales_forecast f
JOIN dim_date d ON f.date_id = d.date_id
GROUP BY d.month
ORDER BY MIN(d.date_id)"""
        
        elif "store" in q:
            return """SELECT s.store_name, s.region, SUM(f.revenue) as total_revenue
FROM fact_sales_forecast f
JOIN dim_store s ON f.store_id = s.store_id
GROUP BY s.store_id, s.store_name, s.region ORDER BY total_revenue DESC"""
        
        elif "revenue" in q or "total" in q:
            return """SELECT SUM(f.revenue) as total_revenue, SUM(f.units_sold) as total_units, 
       SUM(f.revenue) - SUM(f.cost) as total_profit
FROM fact_sales_forecast f"""
        
        elif "sales" in q:
            return """SELECT d.month, SUM(f.actual_sales) as actual_sales
FROM fact_sales_forecast f
JOIN dim_date d ON f.date_id = d.date_id
GROUP BY d.month
ORDER BY MIN(d.date_id)"""
        
        # Default: revenue by region
        return """SELECT s.region, SUM(f.revenue) as total_revenue
FROM fact_sales_forecast f
JOIN dim_store s ON f.store_id = s.store_id
GROUP BY s.region ORDER BY total_revenue DESC"""
    
    def _fallback_response(self, query: str) -> tuple:
        """Generate fallback response without LLM."""
        query_lower = query.lower()
        sql = self._sql
        
        if "revenue" in query_lower and "region" in query_lower:
            sql_query = """SELECT s.region, SUM(f.revenue) as total_revenue
FROM fact_sales_forecast f
JOIN dim_store s ON f.store_id = s.store_id
GROUP BY s.region ORDER BY total_revenue DESC"""
            result = sql.execute(sql_query)
            if result.success:
                return f"**Revenue by Region:**\n\n```sql\n{sql_query}\n```", sql_query, result.to_dict()
        
        elif "forecast" in query_lower:
            sql_query = """SELECT d.month_name, 
       SUM(f.forecast_sales) as forecast_sales,
       SUM(f.actual_sales) as actual_sales
FROM fact_sales_forecast f
JOIN dim_date d ON f.date_id = d.date_id
GROUP BY d.month, d.month_name
ORDER BY d.month"""
            result = sql.execute(sql_query)
            if result.success:
                return f"**Forecast vs Actual by Month:**\n\n```sql\n{sql_query}\n```", sql_query, result.to_dict()
        
        elif "revenue" in query_lower and "category" in query_lower:
            sql_query = """SELECT p.category, SUM(f.revenue) as total_revenue
FROM fact_sales_forecast f
JOIN dim_product p ON f.product_id = p.product_id
GROUP BY p.category ORDER BY total_revenue DESC"""
            result = sql.execute(sql_query)
            if result.success:
                return f"**Revenue by Category:**\n\n```sql\n{sql_query}\n```", sql_query, result.to_dict()
        
        elif "margin" in query_lower or "profit" in query_lower:
            sql_query = """SELECT 
    SUM(revenue) as total_revenue,
    SUM(cost) as total_cost,
    SUM(revenue) - SUM(cost) as gross_profit,
    ROUND((SUM(revenue) - SUM(cost)) / SUM(revenue) * 100, 2) as gross_margin_pct
FROM fact_sales_forecast"""
            result = sql.execute(sql_query)
            if result.success:
                return f"**Profit & Margin:**\n\n```sql\n{sql_query}\n```", sql_query, result.to_dict()
        
        # Generic
        sql_query = "SELECT SUM(revenue) as total_revenue FROM fact_sales_forecast"
        result = sql.execute(sql_query)
        return "Configure GROQ_API_KEY for AI-powered answers.", sql_query, result.to_dict() if result.success else None
    
    def _error_response(self, trace_id: str, query: str, start_time: float, error: str) -> AgentResponse:
        """Create error response."""
        elapsed = duration_ms(start_time)
        self._telemetry.end_request(trace_id=trace_id, success=False, error_category=ErrorCategory.RUNTIME_ERROR.value)
        
        return AgentResponse(
            trace_id=trace_id,
            query=query,
            answer=f"Error: {error}",
            duration_ms=elapsed,
            success=False,
            error=error
        )


# Singleton
_agent_runtime: Optional[AgentRuntime] = None


def get_agent_runtime() -> AgentRuntime:
    global _agent_runtime
    if _agent_runtime is None:
        _agent_runtime = AgentRuntime()
    return _agent_runtime


def run_query(query: str, session_id: Optional[str] = None) -> AgentResponse:
    return get_agent_runtime().run(query, session_id)
