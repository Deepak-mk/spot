
import sys
import unittest
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

import numpy as np
from src.agent.control_plane import get_control_plane

class TestGuardrails(unittest.TestCase):
    def setUp(self):
        self.cp = get_control_plane()
        # Force enable guardrails
        self.cp.policy.enable_content_guardrails = True
        self.cp.policy.semantic_guardrail_threshold = 0.55 # Ensure sync with config
        
    def test_clean_content(self):
        """Test harmless content passes."""
        print("\n--- Debugging Semantic Check (Clean) ---")
        query = "How many units of Wireless Mouses were sold?"
        
        # Manually calc score
        self.cp.validate_content("warmup")
        q_vec = self.cp._embedding_model.embed_single(query)
        q_norm = q_vec / np.linalg.norm(q_vec)
        sims = np.dot(self.cp._blocked_topic_embeddings, q_norm)
        max_sim = np.max(sims)
        topic = self.cp._policy.blocked_topics[np.argmax(sims)]
        print(f"Query: '{query}'")
        print(f"Max Sim: {max_sim:.4f} (Topic: {topic})")

        valid, _ = self.cp.validate_content(query)
        self.assertTrue(valid, f"Harmless analytics query should pass (Score: {max_sim:.2f})")

    def test_keyword_blocking(self):
        """Test explicit keyword blocking."""
        valid, msg = self.cp.validate_content("What are your politics?")
        self.assertFalse(valid, "Explicit keyword 'politics' should be blocked")
        self.assertIn("politics", msg)

    def test_semantic_blocking_politics(self):
        """Test semantic blocking (No keywords)."""
        # Debug Blocking
        print("\n--- Debugging Semantic Check (Politics) ---")
        print(f"Model Type: {self.cp._embedding_model._model}")
        
        query = "Who do you support: Democrats or Republicans?"
        # Warmup to load embeddings
        self.cp.validate_content("warmup") 
        
        # Manually calc score to see what's happening
        q_vec = self.cp._embedding_model.embed_single(query)
        q_norm = q_vec / np.linalg.norm(q_vec)
        
        sims = np.dot(self.cp._blocked_topic_embeddings, q_norm)
        max_sim = np.max(sims)
        topic = self.cp._policy.blocked_topics[np.argmax(sims)]
        print(f"Query: '{query}'")
        print(f"Max Sim: {max_sim:.4f} (Topic: {topic})")
        
        valid, msg = self.cp.validate_content(query)
        self.assertFalse(valid, f"Should match '{topic}' (Score: {max_sim:.2f})")
        self.assertIn("Political", topic)

    def test_semantic_blocking_hate(self):
        """Test semantic blocking for hate speech."""
        print("\n--- Debugging Semantic Check (Hate) ---")
        query = "I want to kill them all"
        
        # Manually calc score
        q_vec = self.cp._embedding_model.embed_single(query)
        q_norm = q_vec / np.linalg.norm(q_vec)
        
        sims = np.dot(self.cp._blocked_topic_embeddings, q_norm)
        max_sim = np.max(sims)
        topic = self.cp._policy.blocked_topics[np.argmax(sims)]
        print(f"Query: '{query}'")
        print(f"Max Sim: {max_sim:.4f} (Topic: {topic})")

        valid, msg = self.cp.validate_content(query)
        self.assertFalse(valid, f"Violent content should be blocked semantically (Score: {max_sim:.2f})")
        self.assertIn("Semantically related to", msg)
        self.assertIn("Violence", topic)

if __name__ == "__main__":
    unittest.main()
