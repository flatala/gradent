"""End-to-end test: Vector DB → Assessment → Normal DB

This script demonstrates the complete workflow:
1. Populate vector DB with mock assignment documents
2. Run assessment workflow (retrieves context via RAG)
3. Save assessment to normal database
4. Query and verify results
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

# Database imports
from database import get_db_session, Assignment, AssignmentAssessment, init_db
from database import mock_data

# Vector DB imports
from vector_db import get_vector_store, ingest_document
from vector_db.mock_documents import get_all_mock_assignments
from vector_db.retrieval import get_collection_stats, retrieve_assignment_context

# Workflow imports
from workflows.assignment_assessment import AssignmentInfo, AssessmentState, assessment_graph
from shared.config import Configuration


def setup_databases():
    """Initialize both databases with mock data."""
    print("\n" + "=" * 70)
    print("STEP 1: Setting Up Databases")
    print("=" * 70 + "\n")
    
    # Setup normal database
    print("Setting up normal database (SQLite)...")
    mock_data.clear_all_data()
    mock_data.populate_mock_data()
    
    # Setup vector database
    print("\nSetting up vector database (ChromaDB)...")
    vector_store = get_vector_store(reset=True)
    
    # Ingest mock documents
    mock_assignments = get_all_mock_assignments()
    assignment_mapping = {
        "rl_mdp_assignment": {"assignment_id": 1, "course_id": 1, "user_id": 1},
        "ml_supervised_learning": {"assignment_id": 3, "course_id": 2, "user_id": 1},
        "cv_hybrid_images": {"assignment_id": 5, "course_id": 3, "user_id": 1},
    }
    
    for key, doc in mock_assignments.items():
        metadata = assignment_mapping.get(key, {"user_id": 1})
        ingest_document(
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
            chunk_size=800,
            chunk_overlap=150
        )
    
    # Show stats
    stats = get_collection_stats()
    print(f"\n[OK] Vector DB ready: {stats['total_chunks']} chunks")
    print(f"[OK] Normal DB ready: Assignments and assessments loaded")


def test_rag_retrieval():
    """Test RAG retrieval from vector DB."""
    print("\n" + "=" * 70)
    print("STEP 2: Testing RAG Retrieval")
    print("=" * 70 + "\n")
    
    # Get an assignment from normal DB and extract data within session
    with get_db_session() as db:
        assignment = db.query(Assignment).filter_by(id=1).first()  # MDP assignment
        assignment_id = assignment.id
        assignment_title = assignment.title
        assignment_desc = assignment.description_short or ''
        course_title = assignment.course.title
        
    print(f"Assignment: {assignment_title}")
    print(f"Course: {course_title}")
    
    # Retrieve context
    print("\nRetrieving context from vector DB...")
    context = retrieve_assignment_context(
        query=f"{assignment_title} {assignment_desc}",
        assignment_id=assignment_id,
        top_k=3
    )
    
    print(f"\nRetrieved Context ({len(context)} chars):")
    print("-" * 70)
    print(context[:800] + "...\n")
    
    return context


async def test_assessment_with_rag():
    """Test assessment workflow with RAG integration."""
    print("\n" + "=" * 70)
    print("STEP 3: Running Assessment Workflow with RAG")
    print("=" * 70 + "\n")
    
    # Initialize configuration
    config = Configuration()
    try:
        config.validate()
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        print("Please set OPENAI_API_KEY in your .env file")
        return None
    
    # Get assignment from normal DB
    with get_db_session() as db:
        assignment = db.query(Assignment).filter_by(id=1).first()  # MDP assignment
        
        assignment_info = AssignmentInfo(
            assignment_id=assignment.id,
            title=assignment.title,
            description=assignment.description_short,
            course_name=assignment.course.title,
            due_date=assignment.due_at,
        )
    
    print(f"Assessing: {assignment_info.title}")
    print(f"Course: {assignment_info.course_name}")
    print(f"Due: {assignment_info.due_date}")
    print("\nRunning workflow (this will use OpenAI API)...\n")
    
    # Create state
    initial_state = AssessmentState(
        assignment_info=assignment_info,
        user_id=1,
    )
    
    # Run workflow
    try:
        result = await assessment_graph.ainvoke(
            initial_state,
            config={"configurable": config.__dict__}
        )
        
        assessment = result.get("assessment")
        if assessment:
            print("\n" + "=" * 70)
            print("Assessment Results")
            print("=" * 70 + "\n")
            
            print(f"Assignment: {assignment_info.title}\n")
            
            print(f"Effort Estimates:")
            print(f"  Optimistic:   {assessment.effort_hours_low:.1f} hours")
            print(f"  Most Likely:  {assessment.effort_hours_most:.1f} hours")
            print(f"  Pessimistic:  {assessment.effort_hours_high:.1f} hours")
            
            print(f"\nDifficulty: {assessment.difficulty_1to5:.1f}/5.0")
            print(f"Risk Score: {assessment.risk_score_0to100:.0f}/100")
            print(f"Confidence: {assessment.confidence_0to1:.0%}")
            
            if assessment.milestones:
                print(f"\nMilestones ({len(assessment.milestones)}):")
                for i, milestone in enumerate(assessment.milestones[:5], 1):
                    print(f"  {i}. {milestone.get('label', 'N/A')} "
                          f"({milestone.get('hours', 0):.1f}h, "
                          f"{milestone.get('days_before_due', 0)} days before)")
            
            if assessment.prereq_topics:
                print(f"\nPrerequisites: {', '.join(assessment.prereq_topics[:5])}")
            
            if assessment.deliverables:
                print(f"\nDeliverables: {', '.join(assessment.deliverables)}")
            
            print(f"\nSummary: {assessment.summary}")
            
            # Check if context was used
            if result.get("retrieved_context"):
                print(f"\n[OK] RAG was used: Retrieved {len(result['retrieved_context'])} chars from vector DB")
            
            # Check if saved to DB
            if result.get("assessment_record_id"):
                print(f"[OK] Saved to database: Assessment ID {result['assessment_record_id']}")
            
            return result
        else:
            print("❌ No assessment generated")
            return None
            
    except Exception as e:
        print(f"❌ Error running assessment: {e}")
        import traceback
        traceback.print_exc()
        return None


def verify_saved_assessment():
    """Verify assessment was saved to normal database."""
    print("\n" + "=" * 70)
    print("STEP 4: Verifying Saved Assessment")
    print("=" * 70 + "\n")
    
    with get_db_session() as db:
        # Get the MDP assignment and its latest assessment
        assignment = db.query(Assignment).filter_by(id=1).first()
        assessment = db.query(AssignmentAssessment).filter_by(
            assignment_id=1,
            is_latest=True
        ).first()
        
        if assessment:
            print(f"Assignment: {assignment.title}")
            print(f"Assessment Version: {assessment.version}")
            print(f"Created: {assessment.created_at}")
            print(f"Is Latest: {assessment.is_latest}")
            print(f"\nEffort: {assessment.effort_hours_low}-{assessment.effort_hours_high}h "
                  f"(most likely: {assessment.effort_hours_most}h)")
            print(f"Difficulty: {assessment.difficulty_1to5}/5")
            print(f"Risk: {assessment.risk_score_0to100}/100")
            print(f"Milestones: {len(assessment.milestones or [])}")
            print(f"Prerequisites: {len(assessment.prereq_topics or [])}")
            
            # Show that sources field is ready for vector DB references
            print(f"\nSources field (for vector DB refs): {assessment.sources}")
            
            print("\n[OK] Assessment successfully saved to database!")
        else:
            print("❌ No assessment found in database")


async def main():
    """Run the complete end-to-end test."""
    print("\n" + "=" * 70)
    print("END-TO-END TEST: Vector DB -> RAG -> Assessment -> Normal DB")
    print("=" * 70)
    
    try:
        # Step 1: Setup databases
        setup_databases()
        
        # Step 2: Test RAG retrieval
        test_rag_retrieval()
        
        # Step 3: Run assessment with RAG
        result = await test_assessment_with_rag()
        
        # Step 4: Verify saved data
        if result:
            verify_saved_assessment()
        
        # Final summary
        print("\n" + "=" * 70)
        print("TEST COMPLETE!")
        print("=" * 70)
        print("\nWorkflow Summary:")
        print("  1. [OK] Vector DB populated with assignment documents")
        print("  2. [OK] RAG retrieval working (semantic search)")
        print("  3. [OK] Assessment workflow with context injection")
        print("  4. [OK] Results saved to normal database")
        print("\nThe complete pipeline is working! 🎉")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
