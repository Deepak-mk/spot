"""
Prompt builder for the Agentic Analytics Platform.
Constructs structured prompts with context from retrieval and metadata.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
import json

from src.retrieval.vector_store import SearchResult


SYSTEM_PROMPT = """You are an AI analytics assistant for a sales and forecast dataset.

Your role is to answer business questions about sales, revenue, forecasts, and related metrics.

## Available Data
You have access to a star schema with:
- **fact_sales_forecast**: Sales transactions with actual and forecast values
- **dim_date**: Calendar dimension (dates, quarters, months)
- **dim_product**: Product catalog (name, category, brand)
- **dim_store**: Store locations (name, region, country)

## Key Metrics
- **Revenue**: Total sales amount (SUM of revenue)
- **Gross Profit**: Revenue minus cost
- **Gross Margin**: Gross profit as percentage of revenue
- **Forecast Accuracy**: How close forecasts are to actuals
- **Units Sold**: Total quantity sold

## Instructions
1. Analyze the user's question to understand what they're asking
2. Use the provided context to formulate an accurate answer
3. If you need to query data, specify what SQL query would retrieve it
4. Always explain your reasoning
5. If you cannot answer with the available data, say so clearly

## Response Format
Provide your answer in this format:
- **Answer**: Direct answer to the question
- **Reasoning**: How you arrived at this answer
- **Data Used**: What tables/metrics you referenced
"""


@dataclass
class PromptContext:
    """Context for building a prompt."""
    query: str
    retrieved_chunks: List[SearchResult] = field(default_factory=list)
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    metadata_context: Optional[Dict] = None
    max_context_tokens: int = 3000
    
    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "retrieved_chunks_count": len(self.retrieved_chunks),
            "conversation_turns": len(self.conversation_history),
        }


@dataclass
class BuiltPrompt:
    """A built prompt ready for LLM."""
    system_prompt: str
    user_prompt: str
    messages: List[Dict[str, str]]
    context_used: Dict[str, Any]
    estimated_tokens: int
    
    def to_openai_format(self) -> List[Dict[str, str]]:
        """Convert to OpenAI messages format."""
        return self.messages
    
    def to_dict(self) -> dict:
        return {
            "system_prompt_length": len(self.system_prompt),
            "user_prompt_length": len(self.user_prompt),
            "message_count": len(self.messages),
            "estimated_tokens": self.estimated_tokens,
        }


class PromptBuilder:
    """
    Builds prompts for the analytics agent.
    Combines system instructions, retrieved context, and user query.
    """
    
    def __init__(self, system_prompt: Optional[str] = None):
        self._system_prompt = system_prompt or SYSTEM_PROMPT
    
    def build(self, context: PromptContext) -> BuiltPrompt:
        """
        Build a complete prompt from context.
        
        Args:
            context: PromptContext with query, retrieved chunks, history
        
        Returns:
            BuiltPrompt ready for LLM
        """
        
        # Enhance System Prompt with Semantic Layer & Feedback
        final_system_prompt = self._system_prompt
        
        try:
            from src.agent.semantic_layer import get_semantic_layer
            sl_context = get_semantic_layer().get_context_block()
            final_system_prompt += "\n\n" + sl_context
        except Exception:
            pass
            
        try:
            from src.agent.feedback import get_feedback_manager
            examples = get_feedback_manager().get_few_shot_examples(limit=3)
            if examples:
                final_system_prompt += "\n\n## Proven Examples (From User Feedback)"
                for ex in examples:
                    final_system_prompt += f"\nQ: {ex['user']}\nSQL: {ex['assistant']}\n"
        except Exception:
            pass

        # Build context section from retrieved chunks
        context_section = self._build_context_section(context.retrieved_chunks)
        
        # Build user prompt
        user_prompt = self._build_user_prompt(context.query, context_section)
        
        # Build messages list
        messages = self._build_messages(
            final_system_prompt,
            user_prompt,
            context.conversation_history
        )
        
        # Estimate tokens (rough: 4 chars per token)
        total_text = final_system_prompt + user_prompt
        for msg in context.conversation_history:
            total_text += msg.get("content", "")
        estimated_tokens = len(total_text) // 4
        
        return BuiltPrompt(
            system_prompt=final_system_prompt,
            user_prompt=user_prompt,
            messages=messages,
            context_used={
                "chunks_count": len(context.retrieved_chunks),
                "chunk_types": [r.metadata.get("chunk_type") for r in context.retrieved_chunks],
                "history_turns": len(context.conversation_history),
                "feedback_examples": len(examples) if 'examples' in locals() else 0
            },
            estimated_tokens=estimated_tokens
        )
    
    def _build_context_section(self, chunks: List[SearchResult]) -> str:
        """Build the context section from retrieved chunks."""
        if not chunks:
            return ""
        
        context_parts = ["## Relevant Context\n"]
        
        for i, chunk in enumerate(chunks, 1):
            chunk_type = chunk.metadata.get("chunk_type", "unknown")
            context_parts.append(f"### {chunk_type.title()} {i}")
            context_parts.append(chunk.content)
            context_parts.append("")  # Empty line
        
        return "\n".join(context_parts)
    
    def _build_user_prompt(self, query: str, context_section: str) -> str:
        """Build the user prompt with query and context."""
        parts = []
        
        if context_section:
            parts.append(context_section)
            parts.append("---\n")
        
        parts.append(f"## User Question\n{query}")
        
        return "\n".join(parts)
    
    def _build_messages(
        self,
        system_prompt: str,
        user_prompt: str,
        history: List[Dict[str, str]]
    ) -> List[Dict[str, str]]:
        """Build the messages list in OpenAI format."""
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # Add conversation history
        for msg in history:
            messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })
        
        # Add current user prompt
        messages.append({"role": "user", "content": user_prompt})
        
        return messages
    
    def build_simple(self, query: str, context_chunks: List[SearchResult] = None) -> BuiltPrompt:
        """Convenience method for simple prompt building."""
        context = PromptContext(
            query=query,
            retrieved_chunks=context_chunks or []
        )
        return self.build(context)


def build_prompt(query: str, chunks: List[SearchResult] = None) -> BuiltPrompt:
    """Convenience function to build a prompt."""
    builder = PromptBuilder()
    return builder.build_simple(query, chunks)
