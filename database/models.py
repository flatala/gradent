"""Database models for the study assistant."""
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum

from sqlalchemy import (
    Column, Integer, String, DateTime, Float, JSON, ForeignKey, Boolean, Text, Enum as SQLEnum
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class AssignmentStatus(str, Enum):
    """Assignment completion status."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class StudyBlockStatus(str, Enum):
    """Study block completion status."""
    PLANNED = "planned"
    COMPLETED = "completed"
    PARTIAL = "partial"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class User(Base):
    """User account."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=True)
    timezone = Column(String, default="UTC")
    preferences = Column(JSON, default={})  # preferred_study_hours, max_daily_hours, etc.
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    courses = relationship("Course", back_populates="user", cascade="all, delete-orphan")
    user_assignments = relationship("UserAssignment", back_populates="user", cascade="all, delete-orphan")
    study_history = relationship("StudyHistory", back_populates="user", cascade="all, delete-orphan")
    study_blocks = relationship("StudyBlock", back_populates="user", cascade="all, delete-orphan")


class Course(Base):
    """Academic course."""
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    code = Column(String, nullable=True)  # e.g., "CS-101"
    term = Column(String, nullable=True)  # e.g., "Fall 2024"
    lms_course_id = Column(String, nullable=True)  # External LMS ID
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="courses")
    assignments = relationship("Assignment", back_populates="course", cascade="all, delete-orphan")


class Assignment(Base):
    """Course assignment (universal/LMS-synced data).
    
    This represents the assignment as it exists in the LMS.
    User-specific progress is tracked in UserAssignment.
    """
    __tablename__ = "assignments"

    id = Column(Integer, primary_key=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    
    # Assignment metadata (from LMS)
    title = Column(String, nullable=False)
    description_short = Column(Text, nullable=True)
    due_at = Column(DateTime, nullable=True)
    lms_link = Column(String, nullable=True)
    lms_assignment_id = Column(String, nullable=True)  # External LMS ID (unique per course)
    
    # Assignment properties (from LMS)
    weight_percentage = Column(Float, nullable=True)  # Grade weight in course
    max_points = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    course = relationship("Course", back_populates="assignments")
    assessments = relationship("AssignmentAssessment", back_populates="assignment", cascade="all, delete-orphan")
    user_assignments = relationship("UserAssignment", back_populates="assignment", cascade="all, delete-orphan")


class SuggestionStatus(str, Enum):
    """Lifecycle of a proactive suggestion."""

    PENDING = "pending"          # Generated, awaiting delivery
    NOTIFIED = "notified"        # Sent to one or more channels
    COMPLETED = "completed"      # User confirmed handled
    DISMISSED = "dismissed"      # User dismissed / ignored


class AssignmentAssessment(Base):
    """AI-generated assessment of an assignment's difficulty, effort, and structure.
    
    This is versioned - we can re-assess an assignment and keep history.
    """
    __tablename__ = "assignment_assessments"

    id = Column(Integer, primary_key=True)
    assignment_id = Column(Integer, ForeignKey("assignments.id"), nullable=False)
    version = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_latest = Column(Boolean, default=True)

    # Effort estimates (PERT-like: low, most likely, high)
    effort_hours_low = Column(Float, nullable=True)
    effort_hours_most = Column(Float, nullable=True)
    effort_hours_high = Column(Float, nullable=True)

    # Difficulty and risk
    difficulty_1to5 = Column(Float, nullable=True)  # 1=very easy, 5=very hard
    weight_in_course = Column(Float, nullable=True)  # 0-100, percentage of final grade
    risk_score_0to100 = Column(Float, nullable=True)  # How risky/challenging
    confidence_0to1 = Column(Float, nullable=True)  # AI's confidence in this assessment

    # Structured data (stored as JSON)
    milestones = Column(JSON, default=list)  # [{label, hours, days_before_due}, ...]
    prereq_topics = Column(JSON, default=list)  # List of prerequisite topics/concepts
    deliverables = Column(JSON, default=list)  # What must be submitted
    blocking_dependencies = Column(JSON, default=list)  # External blockers (e.g., partner availability)
    sources = Column(JSON, default=list)  # References to vector DB chunks or URLs used

    # Model metadata
    model_meta = Column(JSON, default={})  # model_name, timestamp, prompt_version, etc.

    # Relationships
    assignment = relationship("Assignment", back_populates="assessments")


class Suggestion(Base):
    """Generated suggestion ready for notification or scheduling."""

    __tablename__ = "suggestions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    category = Column(String, nullable=False)
    priority = Column(String, nullable=True)

    suggested_time = Column(DateTime, nullable=True)
    suggested_time_text = Column(String, nullable=True)

    linked_assignments = Column(JSON, default=list)
    linked_events = Column(JSON, default=list)
    tags = Column(JSON, default=list)
    sources = Column(JSON, default=list)

    channel_config = Column(JSON, default=dict)
    status = Column(SQLEnum(SuggestionStatus), default=SuggestionStatus.PENDING, index=True)

    times_notified = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    delivered_at = Column(DateTime, nullable=True)
    last_notified_at = Column(DateTime, nullable=True)

    user = relationship("User")


class UserAssignment(Base):
    """User-specific assignment tracking (personalized progress and settings).
    
    Links users to assignments with their personal progress, status, and preferences.
    This allows multiple users to work on the same assignment with different progress.
    """
    __tablename__ = "user_assignments"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    assignment_id = Column(Integer, ForeignKey("assignments.id"), nullable=False)
    
    # User-specific status and progress
    status = Column(SQLEnum(AssignmentStatus), default=AssignmentStatus.NOT_STARTED)
    
    # Time tracking (cached/computed fields)
    hours_estimated_user = Column(Float, nullable=True)  # User's own estimate (overrides AI)
    hours_done = Column(Float, default=0.0, nullable=False)  # Sum from study_history
    hours_remaining = Column(Float, nullable=True)  # Computed: uses assessment or user estimate
    last_worked_at = Column(DateTime, nullable=True)  # Last study session timestamp
    
    # User-specific metadata
    notes = Column(Text, nullable=True)  # Personal notes about the assignment
    priority = Column(Integer, nullable=True)  # User can override priority (1-5, 5=highest)
    is_archived = Column(Boolean, default=False)  # Hide from active list after completion
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="user_assignments")
    assignment = relationship("Assignment", back_populates="user_assignments")
    study_history = relationship("StudyHistory", back_populates="user_assignment", cascade="all, delete-orphan")
    study_blocks = relationship("StudyBlock", back_populates="user_assignment", cascade="all, delete-orphan")


class StudyHistory(Base):
    """Records every study session/progress update.
    
    This is the source of truth for progress tracking. All hours_done computations
    aggregate from this table.
    """
    __tablename__ = "study_history"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user_assignment_id = Column(Integer, ForeignKey("user_assignments.id"), nullable=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=True)  # For general course study
    
    # Time and date
    date = Column(DateTime, nullable=False, default=datetime.utcnow)
    minutes = Column(Integer, nullable=False)
    
    # Quality metrics
    focus_rating_1to5 = Column(Integer, nullable=True)  # 1=distracted, 5=deep focus
    quality_rating_1to5 = Column(Integer, nullable=True)  # 1=unproductive, 5=very productive
    
    # Context
    source = Column(String, nullable=False)  # 'scheduled_block', 'ad_hoc', 'calendar_sync'
    study_block_id = Column(Integer, ForeignKey("study_blocks.id"), nullable=True)
    notes = Column(Text, nullable=True)  # User notes about this session
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="study_history")
    user_assignment = relationship("UserAssignment", back_populates="study_history")
    course = relationship("Course")
    study_block = relationship("StudyBlock", back_populates="history_entries")


class StudyBlock(Base):
    """Planned or completed study session.
    
    Represents scheduled study time, either from the scheduler agent or
    user-created. Can be linked to calendar events.
    """
    __tablename__ = "study_blocks"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user_assignment_id = Column(Integer, ForeignKey("user_assignments.id"), nullable=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=True)  # For general course study
    
    # Calendar integration
    calendar_event_id = Column(String, nullable=True)  # Google/Outlook event ID
    calendar_provider = Column(String, nullable=True)  # 'google', 'outlook', 'manual'
    
    # Timing
    start_at = Column(DateTime, nullable=False)
    end_at = Column(DateTime, nullable=False)
    planned_minutes = Column(Integer, nullable=False)
    
    # Completion tracking
    status = Column(SQLEnum(StudyBlockStatus), default=StudyBlockStatus.PLANNED)
    actual_minutes = Column(Integer, nullable=True)  # Filled after completion
    focus_rating_1to5 = Column(Integer, nullable=True)  # Filled after completion
    
    # Metadata
    title = Column(String, nullable=True)  # e.g., "Work on MDP Assignment"
    description = Column(Text, nullable=True)  # What to work on in this block
    notes = Column(Text, nullable=True)  # Post-session notes
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="study_blocks")
    user_assignment = relationship("UserAssignment", back_populates="study_blocks")
    course = relationship("Course")
    history_entries = relationship("StudyHistory", back_populates="study_block", cascade="all, delete-orphan")


class CalendarEvent(Base):
    """Calendar events created by the scheduler agent.
    
    Tracks all calendar events (meetings, study sessions, etc.) created through
    the scheduler workflow. Persists event details for tracking and future reference.
    """
    __tablename__ = "calendar_events"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Google Calendar identifiers
    event_id = Column(String, nullable=False, unique=True)  # Google Calendar event ID
    calendar_id = Column(String, nullable=False)  # Calendar ID (e.g., 'primary')
    
    # Event details
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    location = Column(String, nullable=True)
    
    # Timing
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    
    # Meeting details
    google_meet_url = Column(String, nullable=True)  # Google Meet or other conferencing link
    calendar_link = Column(String, nullable=True)  # Link to view event in Google Calendar
    attendees = Column(JSON, default=list)  # List of attendee email addresses
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User")
