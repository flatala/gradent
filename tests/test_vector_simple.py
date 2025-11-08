"""Simple test to verify vector DB setup without running full assessment."""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

from vector_db import get_vector_store, ingest_document
from vector_db.mock_documents import get_all_mock_assignments
from vector_db.retrieval import get_collection_stats, retrieve_assignment_context

print("\n" + "=" * 60)
print("Vector DB Simple Test")
print("=" * 60 + "\n")

# Initialize vector store
print("1. Initializing vector store...")
vector_store = get_vector_store(reset=True)
print("   [OK] Vector store created\n")

# Ingest one document
print("2. Ingesting sample document...")
mock_assignments = get_all_mock_assignments()
doc = mock_assignments["rl_mdp_assignment"]

ids = ingest_document(
    text=doc['content'],
    doc_id="test_mdp",
    source_type="assignment",
    assignment_id=1,
    course_id=1,
    user_id=1,
    chunk_size=800,
    chunk_overlap=150
)

print(f"   [OK] Ingested {len(ids)} chunks\n")

# Get stats
print("3. Collection statistics:")
stats = get_collection_stats()
print(f"   Total chunks: {stats['total_chunks']}")
print(f"   Source types: {stats['source_types']}\n")

# Test retrieval
print("4. Testing retrieval...")
context = retrieve_assignment_context(
    query="value iteration policy iteration bellman equation",
    assignment_id=1,
    top_k=2
)

print(f"   [OK] Retrieved {len(context)} characters")
print("\nSample context:")
print("-" * 60)
print(context[:400] + "...\n")

print("=" * 60)
print("[OK] Vector DB is working correctly!")
print("=" * 60)
