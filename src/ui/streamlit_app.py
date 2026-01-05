"""
Streamlit UI for the Agentic Analytics Platform.
Full-featured with LLM, SQL, visualizations, and live observability.
"""

import streamlit as st
import sys
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.agent.runtime import run_query, get_agent_runtime
from src.agent.llm_client import get_llm_client
from src.agent.sql_executor import get_sql_executor
from src.agent.memory import get_conversation_memory
from src.agent.control_plane import get_control_plane
from src.retrieval.ingest import ingest_semantic_data
from src.retrieval.vector_store import get_vector_store
from src.observability.telemetry import get_telemetry
from src.observability.tracing import get_tracer
from src.observability.latency import get_latency_tracker
from src.observability.cost import get_cost_tracker


# Page config
st.set_page_config(
    page_title="Agentic Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        color: #6b7280;
        font-size: 1rem;
        margin-bottom: 1rem;
    }
    .log-entry {
        font-family: 'Monaco', 'Menlo', monospace;
        font-size: 0.72rem;
        padding: 0.25rem 0.5rem;
        margin: 0.2rem 0;
        border-radius: 0.25rem;
        border-left: 3px solid;
    }
    .log-info { background: #e0f2fe; border-color: #0284c7; color: #0c4a6e; }
    .log-success { background: #dcfce7; border-color: #16a34a; color: #166534; }
    .log-warning { background: #fef3c7; border-color: #d97706; color: #92400e; }
    .log-error { background: #fee2e2; border-color: #dc2626; color: #991b1b; }
    .log-trace { background: #f3e8ff; border-color: #9333ea; color: #581c87; }
    .log-similarity { background: #ecfdf5; border-color: #059669; color: #065f46; }
    .metric-mini {
        background: linear-gradient(135deg, #f0f4f8 0%, #e2e8f0 100%);
        padding: 0.5rem;
        border-radius: 0.5rem;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .relevance-high { color: #16a34a; font-weight: bold; }
    .relevance-medium { color: #d97706; font-weight: bold; }
    .relevance-low { color: #dc2626; font-weight: bold; }
</style>
""", unsafe_allow_html=True)


def initialize():
    """Initialize session state."""
    if "session_id" not in st.session_state:
        import uuid
        st.session_state.session_id = str(uuid.uuid4())[:16]
    
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "data_loaded" not in st.session_state:
        st.session_state.data_loaded = False
    
    if "logs" not in st.session_state:
        st.session_state.logs = []


def add_log(level: str, message: str, trace_id: str = None):
    """Add a log entry."""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    log = {
        "timestamp": timestamp,
        "level": level,
        "message": message,
        "trace_id": trace_id[:8] if trace_id else None
    }
    if "logs" not in st.session_state:
        st.session_state.logs = []
    st.session_state.logs.append(log)
    if len(st.session_state.logs) > 100:
        st.session_state.logs = st.session_state.logs[-100:]


def load_data():
    """Load semantic data."""
    if not st.session_state.data_loaded:
        add_log("info", "Starting data ingestion...")
        try:
            result = ingest_semantic_data()
            st.session_state.data_loaded = True
            st.session_state.doc_count = result.documents_ingested
            add_log("success", f"Ingested {result.documents_ingested} documents in {result.total_time_ms:.1f}ms")
        except Exception as e:
            add_log("error", f"Ingestion failed: {e}")

def get_valid_charts(df) -> dict:
    """Determine valid chart types for the dataframe."""
    import pandas as pd
    valid = {"Bar": True, "Line": True, "Pie": False, "Scatter": False}
    reasons = {}
    
    numeric_cols = df.select_dtypes(include=['number']).columns
    
    # Pie requires at least 1 numeric
    if len(numeric_cols) >= 1:
        valid["Pie"] = True
    else:
        reasons["Pie"] = "Requires at least 1 numeric column"
        
    # Scatter requires at least 2 numeric
    if len(numeric_cols) >= 2:
        valid["Scatter"] = True
    else:
        reasons["Scatter"] = "Requires at least 2 numeric columns"
        
    return valid, reasons

def render_chart(df, chart_type):
    """Render the selected chart type."""
    numeric_cols = df.select_dtypes(include=['number']).columns
    if len(numeric_cols) == 0:
        st.warning("No numeric data to plot.")
        return

    try:

        import altair as alt
        
        # Check for multi-series (comparison) data
        is_multi_series = len(numeric_cols) > 1
        x_col = df.columns[0] # Assume first column is the dimension (e.g. Month)

        if is_multi_series and chart_type in ["Bar", "Line"]:
            # Transform to long format for Altair
            df_long = df.melt(id_vars=[x_col], value_vars=numeric_cols, var_name='Metric', value_name='Value')
            
            base = alt.Chart(df_long).encode(
                tooltip=[x_col, 'Metric', 'Value']
            )
            
            if chart_type == "Bar":
                # Grouped Bar Chart
                chart = base.mark_bar().encode(
                    x=alt.X(x_col, sort=None),
                    y=alt.Y('Value'),
                    color='Metric',
                    xOffset='Metric' # Creates side-by-side bars
                )
            else: # Line
                chart = base.mark_line(point=True).encode(
                    x=alt.X(x_col, sort=None),
                    y=alt.Y('Value'),
                    color='Metric'
                )
            
            st.altair_chart(chart, use_container_width=True)
            return

        # Single Series visualization
        base = alt.Chart(df).encode(
            tooltip=[x_col, numeric_cols[0]]
        )

        if chart_type == "Bar":
            chart = base.mark_bar().encode(
                x=alt.X(x_col, sort=None),
                y=numeric_cols[0]
            )
            st.altair_chart(chart, use_container_width=True)
            
        elif chart_type == "Line":
            chart = base.mark_line(point=True).encode(
                x=alt.X(x_col, sort=None),
                y=numeric_cols[0]
            )
            st.altair_chart(chart, use_container_width=True)
            
        elif chart_type == "Pie":
            chart = base.mark_arc(outerRadius=120).encode(
                theta=alt.Theta(numeric_cols[0], stack=True),
                color=alt.Color(x_col, sort=None),
                order=alt.Order(numeric_cols[0], sort="descending")
            )
            st.altair_chart(chart, use_container_width=True)
            
        elif chart_type == "Scatter":
            st.scatter_chart(df, x=numeric_cols[0], y=numeric_cols[1])
            
    except Exception as e:
        st.error(f"Could not render chart: {e}")


def render_sidebar():
    """Render sidebar with controls."""
    with st.sidebar:
        st.markdown("## 📊 Control Plane")
        
        control_plane = get_control_plane()
        vs = get_vector_store()
        llm = get_llm_client()
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Documents", vs.count())
        with col2:
            status = "🟢" if not control_plane.kill_switch.is_active() else "🔴"
            st.metric("System", status)
        
        if llm.is_configured():
            st.success("🤖 LLM Connected")
        else:
            st.warning("🤖 Set GROQ_API_KEY in .env")
        
        st.divider()
        
        st.markdown("### 🎯 Actions")
        
        if st.button("📊 Dashboard", use_container_width=True):
            st.session_state.show_dashboard = True
            add_log("info", "Opened analytics dashboard")
            st.rerun()
        
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.messages = []
            memory = get_conversation_memory()
            memory.clear_session(st.session_state.session_id)
            add_log("info", "Chat history cleared")
            st.rerun()
        
        if st.button("🧹 Clear Logs", use_container_width=True):
            st.session_state.logs = []
            st.rerun()
        
        st.divider()
        
        st.markdown("### 🛡️ Safety")
        if control_plane.kill_switch.is_active():
            st.error("🛑 KILL SWITCH ACTIVE")
            if st.button("✅ Disable"):
                control_plane.kill_switch.disable("ui")
                add_log("warning", "Kill switch disabled")
                st.rerun()
        else:
            if st.button("🛑 Kill Switch", use_container_width=True):
                control_plane.kill_switch.enable("Manual trigger", "ui")
                add_log("warning", "Kill switch ENABLED")
                st.rerun()


def render_observability_panel():
    """Render live observability panel."""
    import pandas as pd
    
    st.markdown("### 📡 Deep Observability")
    
    telemetry = get_telemetry()
    cost_tracker = get_cost_tracker()
    latency_tracker = get_latency_tracker()
    
    cost_stats = cost_tracker.get_stats()
    latency_summary = latency_tracker.get_summary()
    
    # 1. Top Metrics
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Queries", len(st.session_state.messages) // 2)
    with c2:
        st.metric("Est. Cost", f"${cost_stats.get('total_cost', 0):.4f}")
    with c3:
        avg = latency_summary.get('average_latency_ms', 0)
        st.metric("Avg Latency", f"{avg:.0f}ms")
    
    st.divider()
    
    # 2. Control Plane Status
    st.markdown("**🛡️ Control Plane**")
    
    try:
        cp = get_control_plane()
        status = cp.get_status()
        
        # Kill Switch Status
        ks = status['kill_switch']
        is_active = ks['enabled']
        ks_color = "red" if is_active else "green"
        ks_text = "HALTED" if is_active else "ACTIVE"
        
        # Budget Status
        cost = status['daily_cost']
        cost_usage = (cost['current_usd'] / cost['limit_usd']) * 100 if cost['limit_usd'] > 0 else 0
        
        cp_c1, cp_c2, cp_c3 = st.columns(3)
        cp_c1.markdown(f"**System Health**\n:{ks_color}[● {ks_text}]")
        cp_c2.markdown(f"**Daily Budget**\n`${cost['current_usd']:.2f} / ${cost['limit_usd']:.2f}`")
        cp_c3.markdown(f"**Model Version**\n`{status['active_model']}`")
        
        if is_active:
             st.error(f"⚠️ Kill Switch Reason: {ks['reason']}")
             
        # Progress bar for budget
        st.progress(min(cost_usage / 100, 1.0), text=f"Budget Usage: {cost_usage:.1f}%")

        # Emergency Controls
        if is_active:
             if st.button("✅ RESTORE SYSTEM", key="obs_restore", use_container_width=True):
                 cp.kill_switch.disable("observability_panel")
                 add_log("warning", "System Restored via Panel")
                 st.rerun()
        else:
             if st.button("🛑 EMERGENCY STOP", key="obs_kill", use_container_width=True):
                 cp.kill_switch.enable("Manual Override", "observability_panel")
                 add_log("error", "Kill Switch Triggered via Panel")
                 st.rerun()
        
    except Exception as e:
        st.error(f"Control Plane Error: {e}")

    st.divider()
    
    # 3. Structured Logs
    st.markdown("**Structured Event Logs**")
    
    if st.session_state.logs:
        df_logs = pd.DataFrame(st.session_state.logs)
        
        # Filter UI
        levels = df_logs['level'].unique().tolist() if 'level' in df_logs else []
        selected_levels = st.multiselect(
            "Filter Level", 
            ["info", "warning", "error", "success", "trace", "similarity"],
            default=[]
        )
        
        if selected_levels:
            df_logs = df_logs[df_logs['level'].isin(selected_levels)]
            
        # Display Dataframe
        st.dataframe(
            df_logs.sort_index(ascending=False), 
            use_container_width=True,
            column_order=["timestamp", "level", "message", "trace_id"],
            column_config={
                "timestamp": st.column_config.TextColumn("Time", width="small"),
                "level": st.column_config.TextColumn("Lvl", width="small"),
                "message": st.column_config.TextColumn("Event", width="large"),
                "trace_id": st.column_config.TextColumn("Trace", width="small"),
            },
            height=400,
            hide_index=True
        )
    else:
        st.info("No logs captured yet.")


def render_dashboard():
    """Render data dashboard."""
    st.markdown("## 📊 Analytics Dashboard")
    
    add_log("info", "Loading dashboard...")
    sql = get_sql_executor()
    
    col1, col2, col3, col4 = st.columns(4)
    
    result = sql.execute("SELECT SUM(revenue) as val FROM fact_sales_forecast")
    with col1:
        if result.success and result.rows:
            st.metric("Total Revenue", f"${result.rows[0][0]:,.0f}")
    
    result = sql.execute("SELECT SUM(revenue) - SUM(cost) as val FROM fact_sales_forecast")
    with col2:
        if result.success and result.rows:
            st.metric("Gross Profit", f"${result.rows[0][0]:,.0f}")
    
    result = sql.execute("SELECT SUM(units_sold) as val FROM fact_sales_forecast")
    with col3:
        if result.success and result.rows:
            st.metric("Units Sold", f"{result.rows[0][0]:,.0f}")
    
    result = sql.execute("SELECT COUNT(DISTINCT store_id) as val FROM fact_sales_forecast")
    with col4:
        if result.success and result.rows:
            st.metric("Stores", f"{result.rows[0][0]}")
    
    st.divider()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Revenue by Region")
        result = sql.execute("""
            SELECT s.region, SUM(f.revenue) as revenue
            FROM fact_sales_forecast f
            JOIN dim_store s ON f.store_id = s.store_id
            GROUP BY s.region ORDER BY revenue DESC
        """)
        if result.success:
            import pandas as pd
            df = pd.DataFrame(result.rows, columns=result.columns)
            st.bar_chart(df.set_index("region"))
    
    with col2:
        st.markdown("### Revenue by Category")
        result = sql.execute("""
            SELECT p.category, SUM(f.revenue) as revenue
            FROM fact_sales_forecast f
            JOIN dim_product p ON f.product_id = p.product_id
            GROUP BY p.category ORDER BY revenue DESC
        """)
        if result.success:
            import pandas as pd
            df = pd.DataFrame(result.rows, columns=result.columns)
            st.bar_chart(df.set_index("category"))
    
    st.markdown("### Monthly Revenue Trend")
    result = sql.execute("""
        SELECT d.month, d.month_name, SUM(f.revenue) as revenue
        FROM fact_sales_forecast f
        JOIN dim_date d ON f.date_id = d.date_id
        GROUP BY d.month, d.month_name ORDER BY d.month
    """)
    if result.success:
        import pandas as pd
        df = pd.DataFrame(result.rows, columns=result.columns)
        st.line_chart(df.set_index("month_name")["revenue"])
    
    add_log("success", "Dashboard loaded")
    
    if st.button("← Back to Chat"):
        st.session_state.show_dashboard = False
        st.rerun()



def handle_feedback(trace_id, query, sql, rating):
    """Callback for feedback buttons."""
    from src.agent.feedback import get_feedback_manager
    get_feedback_manager().record_feedback(trace_id, query, sql, rating)
    st.toast(f"Feedback ({'👍' if rating==1 else '👎'}) recorded! The agent will learn from this.")

def render_chat():
    """Render chat interface."""
    import pandas as pd
    
    # Example queries
    if not st.session_state.messages:
        st.markdown("### 💡 Try these queries:")
        examples = [
            "What is the total revenue by region?",
            "Show revenue by product category",
            "What is the gross margin percentage?",
            "Show forecast vs actual by month"
        ]
        cols = st.columns(2)
        for i, example in enumerate(examples):
            with cols[i % 2]:
                if st.button(example, key=f"ex_{i}", use_container_width=True):
                    st.session_state.pending_query = example
                    st.rerun()
    
    # Chat history
    for i, msg in enumerate(st.session_state.messages):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            
            if msg["role"] == "assistant":
                # Show retrieved context with similarity scores
                if msg.get("retrieved_context"):
                    with st.expander("🔍 Retrieved Context (Similarity Scores)", expanded=False):
                        for ctx in msg["retrieved_context"]:
                            rel_class = f"relevance-{ctx['relevance'].lower()}"
                            st.markdown(f"""
                            **{ctx['chunk_type'].title()}** 
                            <span class="{rel_class}">({ctx['similarity_score']:.4f} - {ctx['relevance']})</span>
                            <br><small>{ctx['content']}</small>
                            """, unsafe_allow_html=True)
                
                # Show SQL
                if msg.get("sql_query"):
                    with st.expander("🔍 SQL Query", expanded=False):
                        st.code(msg["sql_query"], language="sql")
                
                # Show data and chart
                if msg.get("sql_result") and msg["sql_result"].get("rows"):
                    with st.expander("📊 Data & Chart", expanded=True):
                        df = pd.DataFrame(msg['sql_result']["rows"], columns=msg['sql_result']["columns"])
                
                        c1, c2 = st.columns([3, 1])
                        valid_charts, reasons = get_valid_charts(df)
                        options = ["Bar", "Line", "Pie", "Scatter"]
                        
                        with c2:
                            chart_type = st.selectbox(
                                "Chart Type", 
                                options, 
                                key=f"hist_{msg['trace_id']}",
                                label_visibility="collapsed"
                            )
                        
                        with c1:
                            st.dataframe(df, use_container_width=True, height=200)

                        if valid_charts.get(chart_type, False):
                            render_chart(df, chart_type)
                        else:
                            st.warning(f"⚠️ {chart_type} Chart is not available: {reasons.get(chart_type, 'Invalid data')}")
                            render_chart(df, "Bar")
                
                # Show metadata
                if msg.get("duration_ms"):
                    st.caption(f"⏱️ {msg['duration_ms']:.0f}ms | Trace: `{msg.get('trace_id', 'N/A')[:8]}...`")
                
                # Feedback Controls
                if msg.get("sql_query"):
                     fc1, fc2, _ = st.columns([1, 1, 10])
                     fc1.button("👍", key=f"up_{i}", on_click=handle_feedback, args=(msg.get("trace_id"), msg.get("query_text", ""), msg["sql_query"], 1), help="Correct Analysis")
                     fc2.button("👎", key=f"down_{i}", on_click=handle_feedback, args=(msg.get("trace_id"), msg.get("query_text", ""), msg["sql_query"], -1), help="Incorrect/Hallucination")
    
    # Handle pending query
    if st.session_state.get("pending_query"):
        query = st.session_state.pending_query
        del st.session_state.pending_query
        process_query(query)
    
    # Chat input
    if query := st.chat_input("Ask about revenue, forecasts, products..."):
        process_query(query)


def process_query(query: str):
    """Process a user query with live logging."""
    import pandas as pd
    import time
    
    trace_id = f"{int(time.time()*1000)}"[:12]
    
    add_log("info", f"Query: {query[:50]}...", trace_id)
    
    st.session_state.messages.append({"role": "user", "content": query})
    
    with st.chat_message("user"):
        st.markdown(query)
    
    add_log("trace", "Retrieving context...", trace_id)
    
    with st.chat_message("assistant"):
        with st.spinner("Analyzing..."):
            result = run_query(query, st.session_state.session_id)
        
        # Log similarity scores
        if getattr(result, 'retrieved_context', None):
            for ctx in getattr(result, 'retrieved_context', [])[:3]:
                add_log("similarity", f"{ctx['chunk_type']}: {ctx['similarity_score']:.4f} ({ctx['relevance']})", trace_id)
        
        if result.sql_query:
            add_log("info", f"SQL: {result.sql_query[:40]}...", trace_id)
        
        if result.sql_result:
            add_log("success", f"Returned {result.sql_result.get('row_count', 0)} rows", trace_id)
        
        st.markdown(result.answer)
        
        # Show retrieved context with scores
        if getattr(result, 'retrieved_context', None):
            with st.expander("🔍 Retrieved Context (Similarity Scores)", expanded=False):
                for ctx in getattr(result, 'retrieved_context', []):
                    rel_color = "#16a34a" if ctx['relevance'] == "High" else "#d97706" if ctx['relevance'] == "Medium" else "#dc2626"
                    st.markdown(f"""
                    **{ctx['chunk_type'].title()}** 
                    <span style="color:{rel_color};font-weight:bold;">({ctx['similarity_score']:.4f} - {ctx['relevance']})</span>
                    <br><small style="color:#666;">{ctx['content']}</small>
                    """, unsafe_allow_html=True)
        
        # Show SQL
        if result.sql_query:
            with st.expander("🔍 SQL Query", expanded=False):
                st.code(result.sql_query, language="sql")
        
        # Show data and chart
        if result.sql_result and result.sql_result.get("rows"):
            with st.expander("📊 Data & Chart", expanded=True):
                df = pd.DataFrame(result.sql_result["rows"], columns=result.sql_result["columns"])
                
                # Layout: Data on left (implicitly), Controls on top right
                c1, c2 = st.columns([3, 1])
                
                valid_charts, reasons = get_valid_charts(df)
                options = ["Bar", "Line", "Pie", "Scatter"]
                
                with c2:
                    chart_type = st.selectbox(
                        "Chart Type", 
                        options, 
                        key=f"chart_{result.trace_id}",
                        label_visibility="collapsed"
                    )
                
                with c1:
                    st.dataframe(df, use_container_width=True, height=200)

                # Validation and Rendering
                if valid_charts.get(chart_type, False):
                    render_chart(df, chart_type)
                else:
                    st.warning(f"⚠️ {chart_type} Chart is not available: {reasons.get(chart_type, 'Invalid data')}")
                    # Fallback to Bar
                    render_chart(df, "Bar")
        
        st.caption(f"⏱️ {result.duration_ms:.0f}ms | Trace: `{result.trace_id[:8]}...`")
    
    add_log("success", f"Response in {result.duration_ms:.0f}ms", trace_id)
    
    # Store message
    st.session_state.messages.append({
        "role": "assistant",
        "query_text": query,
        "content": result.answer,
        "sql_query": result.sql_query,
        "sql_result": result.sql_result,
        "retrieved_context": getattr(result, 'retrieved_context', []),
        "duration_ms": result.duration_ms,
        "trace_id": result.trace_id
    })
    
    st.rerun()


def main():
    """Main application."""
    initialize()
    load_data()
    
    st.markdown('<p class="main-header">📊 Agentic Analytics Platform</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">AI-powered analytics with real-time observability</p>', unsafe_allow_html=True)
    
    render_sidebar()
    
    if st.session_state.get("show_dashboard"):
        render_dashboard()
    else:
        col1, col2 = st.columns([2, 1])
        
        with col2:
            render_observability_panel()
        
        with col1:
            render_chat()


if __name__ == "__main__":
    main()
