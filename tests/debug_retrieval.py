
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from src.retrieval.vector_store import get_vector_store
from src.retrieval.ingest import ingest_semantic_data

def debug_retrieval():
    print("Ingesting data...")
    ingest_semantic_data()
    
    vs = get_vector_store()
    print(f"Vector Store Count: {vs.count()}")
    
    query = "What are the total earnings?"
    print(f"\nQuery: {query}")
    
    results = vs.search(query, top_k=5)
    
    print("\n--- Retrieved Chunks ---")
    for i, res in enumerate(results):
        print(f"\n#{i+1} Score: {res.score:.4f}")
        print(f"Source: {res.metadata.get('chunk_type', 'unknown')}")
        print(f"Content:\n{res.content}")

if __name__ == "__main__":
    debug_retrieval()
