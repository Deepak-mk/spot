
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from src.agent.runtime import run_query
from src.utils.config import get_settings

def debug_agent():
    print("Running Agent Query...")
    
    # Ensure guardrails don't block us (or do, and we see steps)
    query = "Show me the total revenue by region"
    response = run_query(query, session_id="debug_session")
    
    print(f"\nResponse: {response.answer[:100]}...")
    print(f"Success: {response.success}")
    
    print("\n--- Thought Trace ---")
    if response.steps:
        for i, step in enumerate(response.steps):
            print(f"{i+1}. {step}")
    else:
        print("NO STEPS CAPTURED!")

if __name__ == "__main__":
    debug_agent()
