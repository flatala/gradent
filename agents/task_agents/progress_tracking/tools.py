"""Progress tracking tools and functions.

These tools enable logging and querying study progress for the feedback loop.
"""
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import re
from sqlalchemy import func, desc

from database import (
    get_db_session,
    UserAssignment,
    StudyHistory,
    StudyBlock,
    StudyBlockStatus,
    AssignmentStatus,
)


def log_study_progress(
    user_id: int,
    assignment_id: Optional[int] = None,
    course_id: Optional[int] = None,
    minutes: int = 0,
    focus_rating: Optional[int] = None,
    quality_rating: Optional[int] = None,
    source: str = "ad_hoc",
    study_block_id: Optional[int] = None,
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    """Log a study session and update progress.
    
    This is the main entry point for recording study time. It:
    1. Creates a StudyHistory entry
    2. Updates UserAssignment (hours_done, hours_remaining, last_worked_at)
    3. Optionally updates StudyBlock status if linked
    4. Returns updated progress information
    
    Args:
        user_id: User ID
        assignment_id: Assignment ID (optional, for assignment-specific study)
        course_id: Course ID (optional, for general course study)
        minutes: Duration of study session
        focus_rating: 1-5 rating of focus level (1=distracted, 5=deep focus)
        quality_rating: 1-5 rating of productivity (1=unproductive, 5=very productive)
        source: 'ad_hoc', 'scheduled_block', or 'calendar_sync'
        study_block_id: Link to StudyBlock if from scheduled session
        notes: User's notes about the session
        
    Returns:
        Dictionary with updated progress info:
        - success: bool
        - message: str
        - hours_logged: float
        - assignment_progress: dict (if assignment_id provided)
        - study_history_id: int
    """
    if minutes <= 0:
        return {
            "success": False,
            "message": "Minutes must be greater than 0",
            "hours_logged": 0.0
        }
    
    if not assignment_id and not course_id:
        return {
            "success": False,
            "message": "Must provide either assignment_id or course_id",
            "hours_logged": 0.0
        }
    
    # Validate focus and quality ratings
    if focus_rating is not None and (focus_rating < 1 or focus_rating > 5):
        focus_rating = None
    if quality_rating is not None and (quality_rating < 1 or quality_rating > 5):
        quality_rating = None
    
    hours = minutes / 60.0
    
    with get_db_session() as db:
        # Get or create UserAssignment if assignment_id provided
        user_assignment = None
        if assignment_id:
            user_assignment = db.query(UserAssignment).filter_by(
                user_id=user_id,
                assignment_id=assignment_id
            ).first()
            
            if not user_assignment:
                # Create UserAssignment if it doesn't exist
                user_assignment = UserAssignment(
                    user_id=user_id,
                    assignment_id=assignment_id,
                    status=AssignmentStatus.IN_PROGRESS,
                    hours_done=0.0
                )
                db.add(user_assignment)
                db.flush()
        
        # Create StudyHistory entry
        study_history = StudyHistory(
            user_id=user_id,
            user_assignment_id=user_assignment.id if user_assignment else None,
            course_id=course_id if not assignment_id else user_assignment.assignment.course_id,
            date=datetime.utcnow(),
            minutes=minutes,
            focus_rating_1to5=focus_rating,
            quality_rating_1to5=quality_rating,
            source=source,
            study_block_id=study_block_id,
            notes=notes
        )
        db.add(study_history)
        db.flush()
        
        # Update UserAssignment if applicable
        assignment_progress = None
        if user_assignment:
            # Update hours_done
            total_minutes = db.query(func.sum(StudyHistory.minutes)).filter(
                StudyHistory.user_assignment_id == user_assignment.id
            ).scalar() or 0
            user_assignment.hours_done = total_minutes / 60.0
            
            # Update hours_remaining (if we have an estimate)
            if user_assignment.hours_remaining is not None:
                user_assignment.hours_remaining = max(
                    user_assignment.hours_remaining - hours,
                    0.0
                )
            
            # Update status to in_progress if it was not_started
            if user_assignment.status == AssignmentStatus.NOT_STARTED:
                user_assignment.status = AssignmentStatus.IN_PROGRESS
            
            # Update last_worked_at
            user_assignment.last_worked_at = datetime.utcnow()
            
            db.flush()
            
            assignment_progress = {
                "assignment_id": assignment_id,
                "assignment_title": user_assignment.assignment.title,
                "status": user_assignment.status.value,
                "hours_done": round(user_assignment.hours_done, 2),
                "hours_remaining": round(user_assignment.hours_remaining, 2) if user_assignment.hours_remaining else None,
                "last_worked_at": user_assignment.last_worked_at.isoformat()
            }
        
        # Update StudyBlock if linked
        if study_block_id:
            study_block = db.query(StudyBlock).filter_by(id=study_block_id).first()
            if study_block:
                study_block.actual_minutes = (study_block.actual_minutes or 0) + minutes
                study_block.focus_rating_1to5 = focus_rating
                
                # Update status based on completion
                if study_block.actual_minutes >= study_block.planned_minutes:
                    study_block.status = StudyBlockStatus.COMPLETED
                else:
                    study_block.status = StudyBlockStatus.PARTIAL
                
                db.flush()
        
        return {
            "success": True,
            "message": f"Logged {minutes} minutes of study time",
            "hours_logged": round(hours, 2),
            "study_history_id": study_history.id,
            "assignment_progress": assignment_progress,
            "focus_rating": focus_rating,
            "quality_rating": quality_rating
        }


def get_assignment_progress(
    user_id: int,
    assignment_id: int
) -> Dict[str, Any]:
    """Get detailed progress for a user's assignment.
    
    Args:
        user_id: User ID
        assignment_id: Assignment ID
        
    Returns:
        Dictionary with progress information:
        - assignment_title: str
        - status: str
        - hours_done: float
        - hours_remaining: float
        - last_worked_at: str (ISO format)
        - total_sessions: int
        - recent_focus_avg: float (last 5 sessions)
        - recent_quality_avg: float (last 5 sessions)
    """
    with get_db_session() as db:
        user_assignment = db.query(UserAssignment).filter_by(
            user_id=user_id,
            assignment_id=assignment_id
        ).first()
        
        if not user_assignment:
            return {
                "success": False,
                "message": "Assignment not found for this user"
            }
        
        # Get study history stats
        history_entries = db.query(StudyHistory).filter_by(
            user_assignment_id=user_assignment.id
        ).order_by(desc(StudyHistory.date)).limit(5).all()
        
        total_sessions = db.query(func.count(StudyHistory.id)).filter(
            StudyHistory.user_assignment_id == user_assignment.id
        ).scalar() or 0
        
        # Calculate average focus and quality from recent sessions
        recent_focus = [h.focus_rating_1to5 for h in history_entries if h.focus_rating_1to5]
        recent_quality = [h.quality_rating_1to5 for h in history_entries if h.quality_rating_1to5]
        
        recent_focus_avg = round(sum(recent_focus) / len(recent_focus), 1) if recent_focus else None
        recent_quality_avg = round(sum(recent_quality) / len(recent_quality), 1) if recent_quality else None
        
        return {
            "success": True,
            "assignment_id": assignment_id,
            "assignment_title": user_assignment.assignment.title,
            "course_name": user_assignment.assignment.course.title,
            "due_at": user_assignment.assignment.due_at.isoformat() if user_assignment.assignment.due_at else None,
            "status": user_assignment.status.value,
            "hours_done": round(user_assignment.hours_done, 2),
            "hours_remaining": round(user_assignment.hours_remaining, 2) if user_assignment.hours_remaining else None,
            "last_worked_at": user_assignment.last_worked_at.isoformat() if user_assignment.last_worked_at else None,
            "total_sessions": total_sessions,
            "recent_focus_avg": recent_focus_avg,
            "recent_quality_avg": recent_quality_avg,
            "priority": user_assignment.priority
        }


def get_user_study_summary(
    user_id: int,
    days: int = 7
) -> Dict[str, Any]:
    """Get a summary of user's study activity over recent days.
    
    Args:
        user_id: User ID
        days: Number of days to look back
        
    Returns:
        Dictionary with summary:
        - total_minutes: int
        - total_sessions: int
        - assignments_worked_on: int
        - avg_focus: float
        - avg_quality: float
        - daily_breakdown: List[dict] (date, minutes)
        - top_assignments: List[dict] (assignment, minutes)
    """
    with get_db_session() as db:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Get all history in time range
        history = db.query(StudyHistory).filter(
            StudyHistory.user_id == user_id,
            StudyHistory.date >= cutoff_date
        ).all()
        
        if not history:
            return {
                "success": True,
                "total_minutes": 0,
                "total_sessions": 0,
                "message": f"No study activity in the last {days} days"
            }
        
        # Calculate totals
        total_minutes = sum(h.minutes for h in history)
        total_sessions = len(history)
        
        # Get unique assignments
        assignment_ids = set(h.user_assignment_id for h in history if h.user_assignment_id)
        
        # Average ratings
        focus_ratings = [h.focus_rating_1to5 for h in history if h.focus_rating_1to5]
        quality_ratings = [h.quality_rating_1to5 for h in history if h.quality_rating_1to5]
        
        avg_focus = round(sum(focus_ratings) / len(focus_ratings), 1) if focus_ratings else None
        avg_quality = round(sum(quality_ratings) / len(quality_ratings), 1) if quality_ratings else None
        
        # Group by assignment
        assignment_minutes = {}
        for h in history:
            if h.user_assignment_id:
                if h.user_assignment_id not in assignment_minutes:
                    ua = db.query(UserAssignment).get(h.user_assignment_id)
                    assignment_minutes[h.user_assignment_id] = {
                        "assignment_title": ua.assignment.title,
                        "minutes": 0
                    }
                assignment_minutes[h.user_assignment_id]["minutes"] += h.minutes
        
        # Sort assignments by time spent
        top_assignments = sorted(
            assignment_minutes.values(),
            key=lambda x: x["minutes"],
            reverse=True
        )[:5]
        
        return {
            "success": True,
            "period_days": days,
            "total_minutes": total_minutes,
            "total_hours": round(total_minutes / 60.0, 1),
            "total_sessions": total_sessions,
            "assignments_worked_on": len(assignment_ids),
            "avg_focus": avg_focus,
            "avg_quality": avg_quality,
            "top_assignments": top_assignments
        }


def parse_progress_from_text(text: str, user_id: int) -> Optional[Dict[str, Any]]:
    """Parse study progress information from natural language text.
    
    This is a helper for LLM agents to extract structured data from user input.
    
    Args:
        text: Natural language text from user
        user_id: User ID (to lookup assignments)
        
    Returns:
        Dictionary with parsed information or None if not a progress update:
        - minutes: int (estimated duration)
        - assignment_keywords: List[str] (for fuzzy matching)
        - focus_indicator: Optional[str] (words suggesting focus level)
        - quality_indicator: Optional[str] (words suggesting productivity)
        - notes: str (original text for context)
        
    Note: This is a simple heuristic parser. LLM agents should do the 
    final interpretation and call log_study_progress with proper values.
    """
    text_lower = text.lower()
    
    # Check if this looks like a progress update
    progress_keywords = [
        "studied", "worked on", "spent", "did", "finished", "completed",
        "practiced", "reviewed", "read", "wrote", "coded", "implemented"
    ]
    
    if not any(keyword in text_lower for keyword in progress_keywords):
        return None
    
    # Extract time duration
    minutes = None
    
    # Patterns like "90 minutes", "1.5 hours", "2h 30m"
    hour_match = re.search(r'(\d+\.?\d*)\s*(?:hour|hr|h)(?:s)?', text_lower)
    minute_match = re.search(r'(\d+)\s*(?:minute|min|m)(?:s)?', text_lower)
    
    if hour_match:
        hours = float(hour_match.group(1))
        minutes = int(hours * 60)
    
    if minute_match:
        mins = int(minute_match.group(1))
        if minutes:
            minutes += mins
        else:
            minutes = mins
    
    # If no explicit time, estimate from context
    if minutes is None:
        if any(word in text_lower for word in ["quick", "briefly", "a bit"]):
            minutes = 30
        elif any(word in text_lower for word in ["long", "extended", "deep"]):
            minutes = 120
        else:
            minutes = 60  # Default assumption
    
    # Extract focus indicators
    focus_indicator = None
    if any(word in text_lower for word in ["focused", "concentrated", "deep work", "productive"]):
        focus_indicator = "high"
    elif any(word in text_lower for word in ["distracted", "interrupted", "struggled"]):
        focus_indicator = "low"
    
    # Extract quality indicators
    quality_indicator = None
    if any(word in text_lower for word in ["finished", "completed", "made progress", "breakthrough"]):
        quality_indicator = "high"
    elif any(word in text_lower for word in ["stuck", "confused", "didn't get much", "wasted"]):
        quality_indicator = "low"
    
    return {
        "minutes": minutes,
        "focus_indicator": focus_indicator,
        "quality_indicator": quality_indicator,
        "notes": text[:500]  # Truncate notes
    }

