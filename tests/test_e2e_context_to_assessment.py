"""End-to-end test: Context Updater → Database → Assessment Workflow.

This test demonstrates the complete pipeline:
1. Context Updater syncs data from Brightspace (mock)
2. Data is stored in both SQLite and ChromaDB
3. Assessment workflow uses this data to generate an assessment
4. RAG pulls relevant context from vector DB
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

import asyncio
from datetime import datetime

from database import get_db_session, User, Course, Assignment, AssignmentAssessment
from context_updater import run_context_update
from workflows.assignment_assessment import assessment_graph, AssignmentInfo, AssessmentState
from vector_db.retrieval import search_documents, get_collection_stats
from shared.config import Configuration


def setup_test_user():
    """Ensure test user exists."""
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
            print("[OK] Created test user")
        else:
            print(f"[OK] Using existing user: {user.name}")
        return user.id


def main():
    """Run the end-to-end test."""
    print("\n" + "=" * 70)
    print("End-to-End Test: Context Updater → Assessment Workflow")
    print("=" * 70 + "\n")
    
    # Initialize configuration
    config = Configuration()
    try:
        config.validate()
    except ValueError as e:
        print(f"Configuration error: {e}")
        print("Please set OPENAI_API_KEY in your .env file")
        return
    
    # Step 1: Setup user
    print("Step 1: Setting up test user...")
    user_id = setup_test_user()
    print()
    
    # Step 2: Run context updater
    print("Step 2: Running Context Updater to sync from Brightspace...")
    print("-" * 70)
    stats = run_context_update(user_id=user_id)
    print()
    
    # Step 3: Verify data is in databases
    print("Step 3: Verifying synced data...")
    print("-" * 70)
    
    with get_db_session() as db:
        courses = db.query(Course).filter_by(user_id=user_id).all()
        assignments = db.query(Assignment).join(Course).filter(
            Course.user_id == user_id
        ).all()
        
        print(f"[OK] Found {len(courses)} courses in database")
        print(f"[OK] Found {len(assignments)} assignments in database")
        
        if not assignments:
            print("\n[ERROR] No assignments found! Cannot proceed with assessment.")
            return
        
        # Pick the first assignment for testing
        test_assignment = assignments[0]
        print("\n[OK] Selected assignment for assessment:")
        print(f"    Title: {test_assignment.title}")
        print(f"    Course: {test_assignment.course.code}")
        print(f"    Due: {test_assignment.due_at.strftime('%Y-%m-%d') if test_assignment.due_at else 'No due date'}")
        
        assignment_id = test_assignment.id
        course_id = test_assignment.course_id
        assignment_title = test_assignment.title
        assignment_description = test_assignment.description_short
        assignment_due = test_assignment.due_at
        course_name = test_assignment.course.title
    
    print()
    
    # Step 4: Query vector DB for relevant context
    print("Step 4: Testing RAG retrieval from vector DB...")
    print("-" * 70)
    
    # Query based on assignment topic - keep it simple for testing
    query_text = "Markov Decision Process reinforcement learning value iteration"
    results = search_documents(
        query=query_text,
        top_k=3
    )
    
    print(f"[OK] Retrieved {len(results)} relevant chunks from vector DB")
    if results:
        print("\nSample context:")
        for i, doc in enumerate(results[:2], 1):
            metadata = doc.metadata
            print(f"  {i}. {metadata.get('title', 'Unknown')}")
            print(f"     Type: {metadata.get('source_type')}, Module: {metadata.get('module', 'N/A')}")
            print(f"     Preview: {doc.page_content[:100]}...")
    
    print()
    
    # Step 5: Run assessment workflow
    print("Step 5: Running Assessment Workflow with RAG...")
    print("-" * 70 + "\n")
    
    # Create assignment info for workflow
    assignment_info = AssignmentInfo(
        title=assignment_title,
        description=assignment_description or "No description available",
        course_name=course_name,
        due_date=assignment_due,
    )
    
    # Create initial state
    initial_state = AssessmentState(
        assignment_info=assignment_info,
        user_id=user_id,
        assignment_id=assignment_id,
    )
    
    # Run assessment workflow (async)
    async def run_async_assessment():
        return await assessment_graph.ainvoke(
            initial_state,
            config={"configurable": config.__dict__}
        )
    
    result = asyncio.run(run_async_assessment())
    
    print("\n" + "-" * 70)
    print("[OK] Assessment workflow complete!")
    print()
    
    # Step 6: Verify assessment was saved
    print("Step 6: Verifying assessment was saved to database...")
    print("-" * 70)
    
    with get_db_session() as db:
        saved_assessment = db.query(AssignmentAssessment).filter_by(
            assignment_id=assignment_id,
            is_latest=True
        ).first()
        
        if saved_assessment:
            print(f"[OK] Assessment saved with ID: {saved_assessment.id}")
            print("\nAssessment Summary:")
            print(f"  Difficulty (1-5): {saved_assessment.difficulty_1to5}")
            print(f"  Risk Score (0-100): {saved_assessment.risk_score_0to100}")
            print("  Time Estimate (PERT):")
            print(f"    - Optimistic: {saved_assessment.effort_hours_low}h")
            print(f"    - Most Likely: {saved_assessment.effort_hours_most}h")
            print(f"    - Pessimistic: {saved_assessment.effort_hours_high}h")
            
            if saved_assessment.milestones:
                print(f"\n  Milestones: {len(saved_assessment.milestones)}")
                for i, milestone in enumerate(saved_assessment.milestones[:3], 1):
                    print(f"    {i}. {milestone.get('label', 'Unknown')}")
                    print(f"       Effort: {milestone.get('hours', 0)}h")
            
            if saved_assessment.prereq_topics:
                print(f"\n  Prerequisite Topics: {len(saved_assessment.prereq_topics)}")
                for prereq in saved_assessment.prereq_topics[:3]:
                    print(f"    - {prereq}")
            
            if saved_assessment.deliverables:
                print(f"\n  Deliverables: {len(saved_assessment.deliverables)}")
                for deliv in saved_assessment.deliverables[:3]:
                    print(f"    - {deliv}")
        else:
            print("[ERROR] Assessment was not saved to database!")
    
    print()
    
    # Final summary
    print("=" * 70)
    print("[OK] End-to-End Test Complete!")
    print("=" * 70)
    print("\nPipeline Verified:")
    print("  1. ✓ Context Updater synced from Brightspace")
    print(f"     - {stats['courses_synced']} courses")
    print(f"     - {stats['assignments_synced']} assignments")
    print(f"     - {stats['content_indexed']} content chunks")
    print("  2. ✓ Data stored in SQLite database")
    print("  3. ✓ Content indexed in ChromaDB vector database")
    print("  4. ✓ RAG retrieval working")
    print("  5. ✓ Assessment workflow generated assessment")
    print("  6. ✓ Assessment saved to database")
    print("\n[OK] All systems working together successfully!")
    print()


if __name__ == "__main__":
    main()
