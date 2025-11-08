"""Database package for the study assistant."""
from .models import (
    Base,
    User,
    Course,
    Assignment,
    AssignmentAssessment,
    AssignmentStatus,
    UserAssignment,
    StudyHistory,
    StudyBlock,
    StudyBlockStatus,
)
from .connection import (
    get_db_session,
    init_db,
    get_db_path,
)

__all__ = [
    "Base",
    "User",
    "Course",
    "Assignment",
    "AssignmentAssessment",
    "AssignmentStatus",
    "UserAssignment",
    "StudyHistory",
    "StudyBlock",
    "StudyBlockStatus",
    "get_db_session",
    "init_db",
    "get_db_path",
]
