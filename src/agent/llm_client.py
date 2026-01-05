"""
LLM Client for the Agentic Analytics Platform.
Supports Groq Cloud API for fast inference.
"""

import os
import json
import time
from dataclasses import dataclass
from typing import List, Dict, Optional, Any
import httpx

from src.utils.config import get_settings
from src.utils.helpers import duration_ms
from src.observability.telemetry import get_telemetry
from src.observability.tracing import TraceEventType


@dataclass
class LLMResponse:
    """Response from LLM."""
    content: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    duration_ms: float
    success: bool
    error: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "content": self.content[:200] + "..." if len(self.content) > 200 else self.content,
            "model": self.model,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "duration_ms": round(self.duration_ms, 2),
            "success": self.success,
            "error": self.error,
        }


class GroqClient:
    """
    Groq Cloud API client for fast LLM inference.
    Uses Llama or Mixtral models via Groq.
    """
    
    BASE_URL = "https://api.groq.com/openai/v1/chat/completions"
    
    # Available Groq models
    MODELS = {
        "llama-3.3-70b": "llama-3.3-70b-versatile",
        "llama-3.1-8b": "llama-3.1-8b-instant",
        "mixtral-8x7b": "mixtral-8x7b-32768",
        "gemma2-9b": "gemma2-9b-it",
    }
    
    def __init__(self, api_key: Optional[str] = None, model: str = "llama-3.1-8b"):
        self._api_key = api_key or os.getenv("GROQ_API_KEY")
        
        # Streamlit Cloud Secrets Fallback
        if not self._api_key:
            try:
                import streamlit as st
                if "GROQ_API_KEY" in st.secrets:
                   self._api_key = st.secrets["GROQ_API_KEY"]
            except ImportError:
                pass
        
        self._model = self.MODELS.get(model, model)
        self._telemetry = get_telemetry()

        # Debug Logging for Deployment
        if self._api_key:
            safe_key = f"{self._api_key[:4]}...{self._api_key[-4:]}" if len(self._api_key) > 8 else "INVALID_LEN"
            print(f"DEBUG: Initialized GroqClient with Key: {safe_key}")
        else:
            print("DEBUG: GroqClient has NO API KEY set")
    
    def is_configured(self) -> bool:
        """Check if API key is configured."""
        return bool(self._api_key)
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.1,
        max_tokens: int = 1024,
        trace_id: Optional[str] = None
    ) -> LLMResponse:
        """
        Send chat completion request to Groq.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            trace_id: Optional trace ID for observability
        
        Returns:
            LLMResponse with content and metadata
        """
        if not self._api_key:
            return LLMResponse(
                content="Error: GROQ_API_KEY not configured. Please set the environment variable.",
                model=self._model,
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                duration_ms=0,
                success=False,
                error="API key not configured"
            )
        
        start_time = time.perf_counter()
        
        # Log start
        if trace_id:
            self._telemetry.add_trace_event(
                trace_id=trace_id,
                event_type=TraceEventType.LLM_CALL_START,
                action=f"Calling Groq API with model {self._model}",
                input_data={"message_count": len(messages)}
            )
        
        try:
            headers = {
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self._model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            
            with httpx.Client(timeout=60.0) as client:
                response = client.post(self.BASE_URL, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
            
            elapsed = duration_ms(start_time)
            
            # Extract response
            choice = data["choices"][0]
            content = choice["message"]["content"]
            usage = data.get("usage", {})
            
            # Track cost
            if trace_id:
                self._telemetry.track_tokens(
                    trace_id=trace_id,
                    model=self._model,
                    prompt_tokens=usage.get("prompt_tokens", 0),
                    completion_tokens=usage.get("completion_tokens", 0)
                )
                
                self._telemetry.add_trace_event(
                    trace_id=trace_id,
                    event_type=TraceEventType.LLM_CALL_END,
                    action="Groq API call completed",
                    duration_ms=elapsed,
                    output_data={"tokens": usage.get("total_tokens", 0)}
                )
            
            return LLMResponse(
                content=content,
                model=self._model,
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                total_tokens=usage.get("total_tokens", 0),
                duration_ms=elapsed,
                success=True
            )
            
        except httpx.HTTPStatusError as e:
            elapsed = duration_ms(start_time)
            error_msg = f"HTTP {e.response.status_code}: {e.response.text[:200]}"
            
            return LLMResponse(
                content=f"Error calling Groq API: {error_msg}",
                model=self._model,
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                duration_ms=elapsed,
                success=False,
                error=error_msg
            )
            
        except Exception as e:
            elapsed = duration_ms(start_time)
            error_msg = str(e)
            
            return LLMResponse(
                content=f"Error: {error_msg}",
                model=self._model,
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                duration_ms=elapsed,
                success=False,
                error=error_msg
            )


# Singleton instance
_groq_client: Optional[GroqClient] = None


def get_llm_client() -> GroqClient:
    """Get the global LLM client instance."""
    global _groq_client
    if _groq_client is None:
        _groq_client = GroqClient()
    return _groq_client


def set_groq_api_key(api_key: str):
    """Set the Groq API key and reinitialize client."""
    global _groq_client
    os.environ["GROQ_API_KEY"] = api_key
    _groq_client = GroqClient(api_key=api_key)
