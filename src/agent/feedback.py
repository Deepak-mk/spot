"""
Feedback Manager for the Agentic Analytics Platform.
Handles persistence of user feedback (positive/negative) to drive reinforcement learning.
"""

import json
from typing import List, Dict, Optional
from pathlib import Path
from dataclasses import dataclass, asdict

from src.utils.helpers import timestamp_now

FEEDBACK_FILE = Path("data/feedback.jsonl")

@dataclass
class FeedbackEntry:
    trace_id: str
    query: str
    sql: str
    rating: int  # 1 (Up) or -1 (Down)
    category: Optional[str] = None  # e.g., "sql_error", "wrong_data", "visualization"
    comment: Optional[str] = None
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = timestamp_now()

class FeedbackManager:
    """Manages recording and retrieving user feedback."""

    def __init__(self):
        FEEDBACK_FILE.parent.mkdir(parents=True, exist_ok=True)

    def record_feedback(self, trace_id: str, query: str, sql: str, rating: int, 
                       comment: Optional[str] = None, category: Optional[str] = None):
        """Save feedback to log file."""
        entry = FeedbackEntry(
            trace_id=trace_id,
            query=query,
            sql=sql,
            rating=rating,
            comment=comment,
            category=category
        )
        
        with open(FEEDBACK_FILE, "a") as f:
            f.write(json.dumps(asdict(entry)) + "\n")

    def get_few_shot_examples(self, limit: int = 5) -> List[Dict]:
        """
        Retrieve positive examples for prompt injection (Few-Shot Learning).
        Returns valid (Query -> SQL) pairs rated positively.
        """
        examples = []
        if not FEEDBACK_FILE.exists():
            return []
            
        try:
            # Read lines in reverse to get recent examples
            with open(FEEDBACK_FILE, "r") as f:
                lines = f.readlines()
                
            for line in reversed(lines):
                if len(examples) >= limit:
                    break
                
                try:
                    data = json.loads(line)
                    # Only use Positive feedback where SQL is present
                    if data["rating"] == 1 and data["sql"] and data["sql"].strip():
                        examples.append({
                            "user": data["query"],
                            "assistant": data["sql"]
                        })
                except json.JSONDecodeError:
                    continue
                    
        except Exception:
            pass
            
        return examples

# Singleton
_feedback_manager = None

def get_feedback_manager() -> FeedbackManager:
    global _feedback_manager
    if _feedback_manager is None:
        _feedback_manager = FeedbackManager()
    return _feedback_manager
