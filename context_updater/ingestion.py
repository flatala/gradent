"""Context Updater ingestion service.

Pulls data from Brightspace and updates both:
1. Normal database (SQLite) - structured data
2. Vector database (ChromaDB) - content for RAG
"""
from datetime import datetime
from typing import List, Dict, Any, Optional
from dateutil import parser as date_parser

from database import (
    get_db_session,
    User,
    Course,
    Assignment,
    AssignmentStatus,
    UserAssignment,
)
from vector_db import ingest_document
from .brightspace_client import MockBrightspaceClient, get_brightspace_client


class ContextUpdater:
    """Service to sync data from Brightspace to local databases.
    
    This is the "ingestion service" that:
    - Fetches courses, assignments, and materials from LMS
    - Normalizes and upserts to relational DB
    - Extracts and indexes content to vector DB
    - Ensures idempotent operations
    """
    
    def __init__(self, user_id: int, brightspace_client: Optional[MockBrightspaceClient] = None):
        """Initialize context updater.
        
        Args:
            user_id: Database user ID
            brightspace_client: Optional Brightspace client (will create mock if not provided)
        """
        self.user_id = user_id
        self.client = brightspace_client or get_brightspace_client(user_id=user_id)
        self.stats = {
            "courses_synced": 0,
            "assignments_synced": 0,
            "content_indexed": 0,
        }
    
    def sync_all(self) -> Dict[str, Any]:
        """Sync all data from Brightspace.
        
        Returns:
            Statistics about the sync operation
        """
        print("\n" + "=" * 70)
        print("Context Updater: Syncing from Brightspace")
        print("=" * 70 + "\n")
        
        # Reset stats
        self.stats = {
            "courses_synced": 0,
            "assignments_synced": 0,
            "content_indexed": 0,
        }
        
        # Sync courses
        print("1. Syncing courses...")
        course_data = self.sync_courses()
        print(f"   [OK] Synced {len(course_data)} courses\n")
        
        # Sync assignments for each course
        print("2. Syncing assignments...")
        total_assignments = 0
        for course_id, lms_course_id in course_data:
            assignments = self.sync_assignments(course_id, lms_course_id)
            total_assignments += len(assignments)
        print(f"   [OK] Synced {total_assignments} assignments\n")
        
        # Index course content to vector DB
        print("3. Indexing course materials to vector DB...")
        total_chunks = 0
        for course_id, lms_course_id in course_data:
            chunks = self.index_course_content(course_id, lms_course_id)
            total_chunks += chunks
        print(f"   [OK] Indexed {total_chunks} content chunks\n")
        
        print("=" * 70)
        print("[OK] Context update complete!")
        print("=" * 70)
        print(f"\nStatistics:")
        print(f"  Courses: {self.stats['courses_synced']}")
        print(f"  Assignments: {self.stats['assignments_synced']}")
        print(f"  Content chunks: {self.stats['content_indexed']}")
        
        return self.stats
    
    def sync_courses(self) -> List[tuple]:
        """Sync courses from Brightspace to normal DB.
        
        Returns:
            List of tuples: (course_id, lms_course_id)
        """
        enrollments = self.client.get_enrollments()
        synced_courses = []
        
        with get_db_session() as db:
            for enrollment in enrollments:
                course_data = enrollment["OrgUnit"]
                
                # Check if course already exists
                existing = db.query(Course).filter_by(
                    user_id=self.user_id,
                    lms_course_id=str(course_data["OrgUnitId"])
                ).first()
                
                if existing:
                    # Update existing course
                    existing.title = course_data["Name"]
                    existing.code = course_data.get("Code")
                    existing.term = self._extract_term(course_data)
                    course = existing
                else:
                    # Create new course
                    course = Course(
                        user_id=self.user_id,
                        title=course_data["Name"],
                        code=course_data.get("Code"),
                        term=self._extract_term(course_data),
                        lms_course_id=str(course_data["OrgUnitId"])
                    )
                    db.add(course)
                
                db.flush()
                # Extract IDs while still in session
                synced_courses.append((course.id, course.lms_course_id))
                self.stats["courses_synced"] += 1
        
        return synced_courses
    
    def sync_assignments(self, course_id: int, lms_course_id: str) -> List[Assignment]:
        """Sync assignments for a course and create UserAssignment records.
        
        Args:
            course_id: Database course ID
            lms_course_id: Brightspace course ID
            
        Returns:
            List of synced Assignment objects
        """
        lms_assignments = self.client.get_assignments(int(lms_course_id))
        synced_assignments = []
        
        with get_db_session() as db:
            for assign_data in lms_assignments:
                # Check if assignment already exists
                lms_link = f"brightspace_{assign_data['Id']}"
                existing = db.query(Assignment).filter_by(
                    course_id=course_id,
                    lms_link=lms_link
                ).first()
                
                # Parse due date
                due_at = None
                if assign_data.get("DueDate"):
                    try:
                        due_at = date_parser.parse(assign_data["DueDate"])
                    except Exception:
                        pass
                
                # Extract description
                description = None
                if assign_data.get("Instructions"):
                    description = assign_data["Instructions"].get("Text", "")
                
                # Extract weight/points
                weight_percentage = None
                max_points = assign_data.get("TotalPoints")
                
                if existing:
                    # Update existing assignment
                    existing.title = assign_data["Name"]
                    existing.description_short = description
                    existing.due_at = due_at
                    existing.max_points = max_points
                    existing.lms_assignment_id = str(assign_data['Id'])
                    assignment = existing
                else:
                    # Create new assignment
                    assignment = Assignment(
                        course_id=course_id,
                        title=assign_data["Name"],
                        description_short=description,
                        due_at=due_at,
                        lms_link=lms_link,
                        lms_assignment_id=str(assign_data['Id']),
                        weight_percentage=weight_percentage,
                        max_points=max_points
                    )
                    db.add(assignment)
                
                db.flush()
                
                # Create/update UserAssignment for this user
                user_assignment = db.query(UserAssignment).filter_by(
                    user_id=self.user_id,
                    assignment_id=assignment.id
                ).first()
                
                if not user_assignment:
                    # Create new UserAssignment
                    user_assignment = UserAssignment(
                        user_id=self.user_id,
                        assignment_id=assignment.id,
                        status=AssignmentStatus.NOT_STARTED,
                        hours_done=0.0
                    )
                    db.add(user_assignment)
                    db.flush()
                
                synced_assignments.append(assignment)
                self.stats["assignments_synced"] += 1
        
        return synced_assignments
    
    def index_course_content(self, course_id: int, lms_course_id: str) -> int:
        """Index course content to vector DB.
        
        Args:
            course_id: Database course ID
            lms_course_id: Brightspace course ID
            
        Returns:
            Number of chunks indexed
        """
        modules = self.client.get_content_modules(int(lms_course_id))
        total_chunks = 0
        
        for module in modules:
            topics = module.get("Topics", [])
            
            for topic in topics:
                if topic.get("Type") == "File" and topic.get("Url"):
                    # Download and index file content
                    try:
                        content = self.client.download_file(topic["Url"])
                        
                        # Ingest to vector DB
                        doc_id = f"content_{lms_course_id}_{topic['Id']}"
                        chunks = ingest_document(
                            text=content,
                            doc_id=doc_id,
                            source_type="lecture",
                            course_id=course_id,
                            user_id=self.user_id,
                            additional_metadata={
                                "title": topic.get("Title"),
                                "description": topic.get("Description"),
                                "module": module.get("Title"),
                                "url": topic.get("Url"),
                            }
                        )
                        
                        total_chunks += len(chunks)
                        self.stats["content_indexed"] += len(chunks)
                        
                    except Exception as e:
                        print(f"   [WARN] Failed to index {topic.get('Title')}: {e}")
        
        return total_chunks
    
    def _extract_term(self, course_data: Dict[str, Any]) -> str:
        """Extract term/semester from course data.
        
        Args:
            course_data: Brightspace course object
            
        Returns:
            Term string (e.g., "Fall 2024")
        """
        # Try to parse from dates
        if course_data.get("StartDate"):
            try:
                start = date_parser.parse(course_data["StartDate"])
                year = start.year
                month = start.month
                
                # Determine semester
                if month >= 8 and month <= 12:
                    return f"Fall {year}"
                elif month >= 1 and month <= 5:
                    return f"Spring {year}"
                else:
                    return f"Summer {year}"
            except Exception:
                pass
        
        return "Unknown Term"


def run_context_update(user_id: int = 1) -> Dict[str, Any]:
    """Run a full context update for a user.
    
    Args:
        user_id: Database user ID
        
    Returns:
        Statistics about the update
    """
    updater = ContextUpdater(user_id=user_id)
    return updater.sync_all()


if __name__ == "__main__":
    # Can be run directly to test
    stats = run_context_update(user_id=1)
    print(f"\n[OK] Complete! {stats}")
