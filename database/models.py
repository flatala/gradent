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
    """Course assignment or project."""
    __tablename__ = "assignments"

    id = Column(Integer, primary_key=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    title = Column(String, nullable=False)
    description_short = Column(Text, nullable=True)
    due_at = Column(DateTime, nullable=True)
    lms_link = Column(String, nullable=True)
    estimated_hours_user = Column(Float, nullable=True)  # User's own estimate
    status = Column(SQLEnum(AssignmentStatus), default=AssignmentStatus.NOT_STARTED)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    course = relationship("Course", back_populates="assignments")
    assessments = relationship("AssignmentAssessment", back_populates="assignment", cascade="all, delete-orphan")


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
