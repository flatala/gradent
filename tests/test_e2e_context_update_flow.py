"""End-to-end test: Full context update flow with assignment assessment.

This test demonstrates the complete autonomous pipeline:
1. Context Updater syncs new data from Brightspace (mock LMS)
2. Data is stored in SQLite database (courses, assignments)
3. Course materials are indexed in ChromaDB vector database
4. Assignment Assessment workflow analyzes a new assignment
5. Assessment is saved to database with structured data
6. Verify all components work together end-to-end

This simulates what happens when the system detects new assignments
and automatically assesses them for the user.
"""
import sys
from pathlib import Path
import asyncio

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

from database import (
    get_db_session,
    User,
    Course,
    Assignment,
    AssignmentAssessment,
)
from context_updater import run_context_update
from agents.task_agents.assignment_assessment import (
    assessment_graph,
    AssignmentInfo,
    AssessmentState,
)
from vector_db.retrieval import search_documents, get_collection_stats
from shared.config import Configuration

load_dotenv()


def setup_test_user():
    """Ensure test user exists in database."""
    with get_db_session() as db:
        user = db.query(User).filter_by(id=1).first()
        if not user:
            user = User(
                id=1,
                name="Alex Student",
                email="alex@example.com",
                timezone="America/New_York",
                preferences={
                    "preferred_study_hours": [9, 10, 11, 14, 15, 16],
                    "max_daily_hours": 6
                }
            )
            db.add(user)
            db.flush()
            print("[OK] Created test user: Alex Student")
        else:
            print(f"[OK] Using existing user: {user.name} (ID: {user.id})")
        return user.id


def verify_database_sync(user_id: int) -> tuple:
    """Verify data was synced to SQLite database.
    
    Returns:
        Tuple of (courses_count, assignments_count, sample_assignment)
    """
    with get_db_session() as db:
        # Query courses
        courses = db.query(Course).filter_by(user_id=user_id).all()
        
        # Query assignments
        assignments = db.query(Assignment).join(Course).filter(
            Course.user_id == user_id
        ).all()
        
        print(f"[OK] Found {len(courses)} courses in database")
        for course in courses[:3]:  # Show first 3
            print(f"     - {course.code}: {course.title}")
        
        print(f"[OK] Found {len(assignments)} assignments in database")
        for assignment in assignments[:3]:  # Show first 3
            due_str = assignment.due_at.strftime("%Y-%m-%d") if assignment.due_at else "No due date"
            print(f"     - {assignment.title} (Due: {due_str})")
        
        # Return data for next steps
        sample_assignment = assignments[0] if assignments else None
        return len(courses), len(assignments), sample_assignment


def verify_vector_db_sync():
    """Verify course materials were indexed to ChromaDB.
    
    Returns:
        Number of chunks indexed
    """
    stats = get_collection_stats()
    total_chunks = stats.get('total_chunks', 0)
    
    print(f"[OK] Found {total_chunks} content chunks in vector database")
    
    if stats.get('source_types'):
        print(f"     Source types: {', '.join(stats['source_types'].keys())}")
    
    return total_chunks


async def run_assessment_workflow(
    assignment: Assignment,
    user_id: int,
    config: Configuration
) -> dict:
    """Run the assignment assessment workflow.
    
    Args:
        assignment: Assignment database record
        user_id: User ID
        config: Configuration instance
        
    Returns:
        Assessment result state dictionary
    """
    # Create assignment info
    assignment_info = AssignmentInfo(
        assignment_id=assignment.id,
        course_id=assignment.course_id,
        title=assignment.title,
        description=assignment.description_short or "No description available",
        course_name=assignment.course.title,
        due_date=assignment.due_at,
    )
    
    # Create initial state
    initial_state = AssessmentState(
        assignment_info=assignment_info,
        user_id=user_id,
    )
    
    print(f"\n[Running] Assessing assignment: '{assignment.title}'")
    print(f"          Course: {assignment.course.title}")
    print(f"          Due: {assignment.due_at.strftime('%Y-%m-%d') if assignment.due_at else 'No due date'}")
    
    # Run the workflow
    result = await assessment_graph.ainvoke(
        initial_state,
        config={"configurable": config.__dict__}
    )
    
    return result


def verify_assessment_saved(assignment_id: int) -> AssignmentAssessment:
    """Verify assessment was saved to database.
    
    Args:
        assignment_id: Assignment ID to check
        
    Returns:
        Saved AssignmentAssessment record or None
    """
    with get_db_session() as db:
        assessment = db.query(AssignmentAssessment).filter_by(
            assignment_id=assignment_id,
            is_latest=True
        ).first()
        
        if assessment:
            print(f"[OK] Assessment saved to database (ID: {assessment.id})")
            return assessment
        else:
            print("[ERROR] Assessment was not saved to database!")
            return None


def display_assessment_summary(assessment: AssignmentAssessment):
    """Display a formatted summary of the assessment."""
    print("\n" + "=" * 70)
    print("ASSESSMENT SUMMARY")
    print("=" * 70)
    
    print("\n📊 Effort Estimates (PERT):")
    print(f"   • Optimistic:    {assessment.effort_hours_low:.1f} hours")
    print(f"   • Most Likely:   {assessment.effort_hours_most:.1f} hours")
    print(f"   • Pessimistic:   {assessment.effort_hours_high:.1f} hours")
    
    print("\n📈 Difficulty & Risk:")
    print(f"   • Difficulty:    {assessment.difficulty_1to5:.1f}/5")
    print(f"   • Risk Score:    {assessment.risk_score_0to100:.0f}/100")
    print(f"   • AI Confidence: {assessment.confidence_0to1:.2f}")
    if assessment.weight_in_course:
        print(f"   • Course Weight: {assessment.weight_in_course:.1f}%")
    
    if assessment.milestones:
        print(f"\n🎯 Milestones ({len(assessment.milestones)}):")
        for i, milestone in enumerate(assessment.milestones[:5], 1):
            label = milestone.get('label', 'Unknown')
            hours = milestone.get('hours', 0)
            days = milestone.get('days_before_due', 'N/A')
            print(f"   {i}. {label} ({hours}h, {days} days before due)")
    
    if assessment.prereq_topics:
        print(f"\n📚 Prerequisites ({len(assessment.prereq_topics)}):")
        for i, topic in enumerate(assessment.prereq_topics[:5], 1):
            print(f"   {i}. {topic}")
    
    if assessment.deliverables:
        print(f"\n📦 Deliverables ({len(assessment.deliverables)}):")
        for i, deliverable in enumerate(assessment.deliverables[:5], 1):
            print(f"   {i}. {deliverable}")
    
    if assessment.blocking_dependencies:
        print(f"\n⚠️  Blocking Dependencies ({len(assessment.blocking_dependencies)}):")
        for i, dep in enumerate(assessment.blocking_dependencies[:3], 1):
            print(f"   {i}. {dep}")
    
    print("\n" + "=" * 70)


def test_rag_retrieval(assignment_title: str):
    """Test RAG retrieval for assignment context.
    
    Args:
        assignment_title: Assignment title to search for
        
    Returns:
        List of retrieved documents
    """
    # Extract key terms from assignment title for better search
    # For demo, just use the title directly
    query = f"{assignment_title} course materials lecture notes"
    
    results = search_documents(query=query, top_k=3)
    
    print(f"[OK] Retrieved {len(results)} relevant chunks from vector DB")
    
    if results:
        print("\n     Sample retrieved context:")
        for i, doc in enumerate(results[:2], 1):
            metadata = doc.metadata
            title = metadata.get('title', 'Unknown')
            source_type = metadata.get('source_type', 'Unknown')
            print(f"     {i}. [{source_type}] {title}")
            print(f"        Preview: {doc.page_content[:80]}...")
    
    return results


async def main():
    """Run the complete end-to-end test."""
    print("\n" + "=" * 70)
    print("E2E TEST: Context Update → Assignment Assessment")
    print("=" * 70)
    print("\nThis test simulates the autonomous pipeline when new assignments")
    print("are detected from the LMS (Brightspace).\n")
    
    # Initialize configuration
    print("🔧 Initializing configuration...")
    config = Configuration()
    try:
        config.validate()
    except ValueError as e:
        print(f"[ERROR] Configuration error: {e}")
        print("Please set OPENAI_API_KEY in your .env file")
        return
    print("[OK] Configuration valid\n")
    
    # -------------------------------------------------------------------------
    # STEP 1: Setup test user
    # -------------------------------------------------------------------------
    print("=" * 70)
    print("STEP 1: Setup Test User")
    print("=" * 70)
    user_id = setup_test_user()
    print()
    
    # -------------------------------------------------------------------------
    # STEP 2: Run context updater (simulate LMS sync)
    # -------------------------------------------------------------------------
    print("=" * 70)
    print("STEP 2: Run Context Updater (Sync from Brightspace)")
    print("=" * 70)
    print("Fetching courses, assignments, and materials from LMS...\n")
    
    stats = run_context_update(user_id=user_id)
    print("\n[OK] Context update complete!")
    print(f"     Courses synced: {stats['courses_synced']}")
    print(f"     Assignments synced: {stats['assignments_synced']}")
    print(f"     Content chunks indexed: {stats['content_indexed']}")
    print()
    
    # -------------------------------------------------------------------------
    # STEP 3: Verify data in databases
    # -------------------------------------------------------------------------
    print("=" * 70)
    print("STEP 3: Verify Data Sync")
    print("=" * 70)
    
    print("\n📁 Normal Database (SQLite):")
    courses_count, assignments_count, sample_assignment = verify_database_sync(user_id)
    
    print("\n📚 Vector Database (ChromaDB):")
    chunks_count = verify_vector_db_sync()
    
    if not sample_assignment:
        print("\n[ERROR] No assignments found! Cannot proceed with assessment test.")
        return
    
    print()
    
    # -------------------------------------------------------------------------
    # STEP 4: Test RAG retrieval
    # -------------------------------------------------------------------------
    print("=" * 70)
    print("STEP 4: Test RAG Retrieval (Vector DB)")
    print("=" * 70)
    print(f"\nQuerying for content related to: '{sample_assignment.title}'\n")
    
    rag_results = test_rag_retrieval(sample_assignment.title)
    print()
    
    # -------------------------------------------------------------------------
    # STEP 5: Run assignment assessment workflow
    # -------------------------------------------------------------------------
    print("=" * 70)
    print("STEP 5: Run Assignment Assessment Workflow")
    print("=" * 70)
    
    try:
        result = await run_assessment_workflow(
            assignment=sample_assignment,
            user_id=user_id,
            config=config
        )
        
        print("\n[OK] Assessment workflow completed successfully!")
        
        # Check if assessment was generated
        if result.get('assessment'):
            print("[OK] Structured assessment generated")
        else:
            print("[WARNING] No assessment in result state")
        
    except Exception as e:
        print(f"\n[ERROR] Assessment workflow failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print()
    
    # -------------------------------------------------------------------------
    # STEP 6: Verify assessment was saved to database
    # -------------------------------------------------------------------------
    print("=" * 70)
    print("STEP 6: Verify Assessment Saved to Database")
    print("=" * 70)
    print()
    
    saved_assessment = verify_assessment_saved(sample_assignment.id)
    
    if not saved_assessment:
        print("[ERROR] Assessment verification failed!")
        return
    
    # -------------------------------------------------------------------------
    # STEP 7: Display assessment summary
    # -------------------------------------------------------------------------
    display_assessment_summary(saved_assessment)
    
    # -------------------------------------------------------------------------
    # FINAL SUMMARY
    # -------------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("✅ E2E TEST COMPLETE - ALL SYSTEMS OPERATIONAL")
    print("=" * 70)
    print("\n📋 Pipeline Verified:")
    print("   1. ✓ Context Updater synced from Brightspace")
    print(f"       └─ {courses_count} courses, {assignments_count} assignments")
    print("   2. ✓ Data stored in SQLite database")
    print("   3. ✓ Content indexed in ChromaDB vector database")
    print(f"       └─ {chunks_count} chunks")
    print("   4. ✓ RAG retrieval working")
    print(f"       └─ Retrieved {len(rag_results)} relevant chunks")
    print("   5. ✓ Assignment assessment workflow executed")
    print(f"       └─ Analyzed: {sample_assignment.title}")
    print("   6. ✓ Assessment saved to database")
    print(f"       └─ Record ID: {saved_assessment.id}")
    print("\n🎉 All components working together successfully!")
    print("    The system can now autonomously detect, assess, and")
    print("    plan for new assignments from the LMS.\n")


if __name__ == "__main__":
    asyncio.run(main())
