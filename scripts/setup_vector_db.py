"""Script to populate vector DB with mock assignment documents."""
import sys
from pathlib import Path

# Add parent directory to path so we can import from root modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from vector_db import get_vector_store, ingest_document, get_vector_db_path
from vector_db.mock_documents import get_all_mock_assignments
from vector_db.retrieval import get_collection_stats
from database import get_db_session, Assignment, init_db, get_db_path


def populate_vector_db(reset: bool = True):
    """Populate vector database with mock assignment documents.

    Args:
        reset: If True, clear existing data first
    """
    print("\n" + "=" * 60)
    print("Populating Vector Database with Mock Documents")
    print("=" * 60 + "\n")

    # Initialize SQL database if it doesn't exist
    db_path = get_db_path()
    if not db_path.exists():
        print("Initializing SQL database...")
        init_db()
    else:
        print(f"SQL database exists at: {db_path}")

    # Initialize (optionally reset)
    vector_store = get_vector_store(reset=reset)
    print(f"Vector DB path: {get_vector_db_path()}\n")
    
    # Get mock assignments
    mock_assignments = get_all_mock_assignments()
    
    # Map assignment keys to database IDs (from mock_data.py)
    # Assignment IDs from mock_data: 1=MDP, 2=Q-Learning, 3=ML Supervised, 4=Randomized Opt, 5=CV Hybrid
    assignment_mapping = {
        "rl_mdp_assignment": {"assignment_id": 1, "course_id": 1, "user_id": 1},
        "ml_supervised_learning": {"assignment_id": 3, "course_id": 2, "user_id": 1},
        "cv_hybrid_images": {"assignment_id": 5, "course_id": 3, "user_id": 1},
    }
    
    # Ingest each assignment
    total_chunks = 0
    for key, doc in mock_assignments.items():
        print(f"Ingesting: {doc['title']}")
        print(f"  Course: {doc['course']}")
        
        # Get metadata from mapping
        metadata = assignment_mapping.get(key, {"user_id": 1})
        
        # Ingest document
        ids = ingest_document(
            text=doc['content'],
            doc_id=f"assignment_{key}",
            source_type="assignment",
            user_id=metadata.get("user_id"),
            course_id=metadata.get("course_id"),
            assignment_id=metadata.get("assignment_id"),
            additional_metadata={
                "title": doc['title'],
                "course": doc['course'],
            },
            chunk_size=800,  # Smaller chunks for better retrieval
            chunk_overlap=150
        )
        
        total_chunks += len(ids)
        print(f"  ✓ Added {len(ids)} chunks\n")
    
    # Show statistics
    print("=" * 60)
    print("Vector DB Population Complete!")
    print("=" * 60)
    print(f"\nTotal chunks ingested: {total_chunks}")
    
    stats = get_collection_stats()
    print(f"\nCollection statistics:")
    print(f"  Total chunks: {stats['total_chunks']}")
    print(f"  Source types: {stats['source_types']}")
    print(f"  Metadata fields: {stats['metadata_fields']}")
    print()


def verify_vector_db():
    """Verify vector DB contents with some sample queries."""
    from vector_db.retrieval import retrieve_assignment_context
    
    print("\n" + "=" * 60)
    print("Vector DB Verification - Sample Queries")
    print("=" * 60 + "\n")
    
    # Test query 1: MDP assignment
    print("Query 1: 'Value iteration and policy iteration for MDPs'")
    print("-" * 60)
    context = retrieve_assignment_context(
        query="value iteration policy iteration bellman equation",
        assignment_id=1,
        top_k=2
    )
    print(context[:500] + "...\n")
    
    # Test query 2: ML assignment
    print("Query 2: 'Supervised learning algorithms comparison'")
    print("-" * 60)
    context = retrieve_assignment_context(
        query="supervised learning decision trees neural networks SVM",
        assignment_id=3,
        top_k=2
    )
    print(context[:500] + "...\n")
    
    # Test query 3: Course-level search
    print("Query 3: 'Computer vision filtering techniques'")
    print("-" * 60)
    context = retrieve_assignment_context(
        query="image filtering convolution frequency domain",
        course_id=3,
        top_k=2
    )
    print(context[:500] + "...\n")
    
    print("=" * 60)
    print("✓ Verification complete!")
    print("=" * 60)


if __name__ == "__main__":
    import sys
    
    # Check if reset flag is provided
    reset = True
    if len(sys.argv) > 1 and sys.argv[1] == "--no-reset":
        reset = False
    
    if reset:
        response = input("This will reset the vector database. Continue? (y/n): ")
        if response.lower() != 'y':
            print("Cancelled.")
            sys.exit(0)
    
    # Populate vector DB
    populate_vector_db(reset=reset)
    
    # Verify
    print("\nWould you like to run verification queries? (y/n): ", end="")
    response = input()
    if response.lower() == 'y':
        verify_vector_db()
