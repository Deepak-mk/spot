"""
Input form component for the Streamlit UI.
"""

import streamlit as st
from typing import Optional, Callable


def render_query_input(
    placeholder: str = "Ask about revenue, forecasts, products...",
    on_submit: Optional[Callable[[str], None]] = None
) -> Optional[str]:
    """
    Render a query input form.
    
    Args:
        placeholder: Placeholder text
        on_submit: Callback when query is submitted
    
    Returns:
        Query string if submitted, None otherwise
    """
    with st.form(key="query_form", clear_on_submit=True):
        query = st.text_input(
            "Your Question",
            placeholder=placeholder,
            label_visibility="collapsed"
        )
        
        col1, col2 = st.columns([4, 1])
        with col2:
            submitted = st.form_submit_button("Ask 🔍", use_container_width=True)
        
        if submitted and query.strip():
            if on_submit:
                on_submit(query.strip())
            return query.strip()
    
    return None


def render_advanced_options() -> dict:
    """
    Render advanced query options.
    
    Returns:
        Dict with options
    """
    with st.expander("⚙️ Advanced Options", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            top_k = st.slider(
                "Context chunks",
                min_value=1,
                max_value=10,
                value=5,
                help="Number of context chunks to retrieve"
            )
        
        with col2:
            show_reasoning = st.checkbox(
                "Show reasoning",
                value=True,
                help="Display agent reasoning steps"
            )
        
        return {
            "top_k": top_k,
            "show_reasoning": show_reasoning
        }


def render_example_queries_grid(examples: list, on_select: Optional[Callable[[str], None]] = None):
    """
    Render a grid of example queries.
    
    Args:
        examples: List of example query strings
        on_select: Callback when an example is clicked
    """
    st.markdown("#### 💡 Example Queries")
    
    # Create 2-column grid
    cols = st.columns(2)
    
    for i, example in enumerate(examples):
        with cols[i % 2]:
            if st.button(
                example,
                key=f"example_query_{i}",
                use_container_width=True,
                type="secondary"
            ):
                if on_select:
                    on_select(example)
                return example
    
    return None
