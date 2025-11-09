# Exam Results & Scheduler Integration Guide

This guide explains how exam assessment results integrate with the scheduler to provide personalized study time recommendations.

## Overview

When a student completes a mock exam:
1. **Assessment**: The system evaluates their performance and recommends study hours
2. **Storage**: Results are saved to the `exam_results` table
3. **Scheduler Integration**: The scheduler uses these results to adjust study time allocation

## Database Schema

### ExamResult Model

```python
class ExamResult(Base):
    """Mock exam results for tracking student performance."""
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    assignment_id = Column(Integer, ForeignKey("assignments.id"))
    
    # Exam metadata
    exam_type = Column(String)  # 'multiple-choice', 'open-ended', 'custom'
    total_questions = Column(Integer)
    
    # Performance metrics
    score = Column(Integer)  # Number correct
    percentage = Column(Float)  # Score as percentage
    
    # AI recommendations
    study_hours_recommended = Column(Float)  # Extracted from AI
    study_recommendation_text = Column(Text)  # Full recommendation
    
    # Detailed results (JSON)
    questions = Column(JSON)  # Question texts and options
    user_answers = Column(JSON)  # User's answers
    correct_answers = Column(JSON)  # Correct answers
    
    completed_at = Column(DateTime)
```

## How It Works

### 1. Exam Assessment Flow

```
Student Takes Exam
       ↓
Frontend sends to /api/assess-exam
       ↓
Backend calculates score
       ↓
LLM analyzes performance → Recommends study hours
       ↓
Results saved to exam_results table
       ↓
Response sent to frontend with recommendation
```

### 2. Study Hour Recommendation Logic

The AI recommends study hours based on performance:

- **90-100%**: 1-2 hours (review and consolidation)
- **70-89%**: 2-4 hours (targeted practice on weak areas)
- **50-69%**: 4-6 hours (substantial study needed)
- **Below 50%**: 6-8 hours (comprehensive review required)

### 3. Scheduler Integration

The scheduler can query exam results to adjust time allocation:

```python
from database.models import ExamResult

# Get latest exam result for an assignment
latest_exam = db.query(ExamResult).filter(
    ExamResult.user_id == user_id,
    ExamResult.assignment_id == assignment_id
).order_by(ExamResult.completed_at.desc()).first()

if latest_exam:
    recommended_hours = latest_exam.study_hours_recommended
    # Use this to override or adjust UserAssignment.hours_remaining
```

## Integration with Scheduler Workflow

### Option 1: Override UserAssignment Hours

Update the `UserAssignment` table when exam is completed:

```python
# In assess_exam endpoint (already implemented):
user_assignment = db.query(UserAssignment).filter(
    UserAssignment.user_id == user_id,
    UserAssignment.assignment_id == assignment_id
).first()

if user_assignment and study_hours:
    user_assignment.hours_estimated_user = study_hours
    user_assignment.hours_remaining = study_hours
    db.commit()
```

### Option 2: Scheduler Reads Exam Results

Modify `workflows/scheduler/tools.py` to check for exam results:

```python
def get_assignment_time_estimate(db: Session, user_id: int, assignment_id: int) -> float:
    """Get time estimate, preferring exam-based recommendations."""
    
    # Check for recent exam results
    recent_exam = db.query(ExamResult).filter(
        ExamResult.user_id == user_id,
        ExamResult.assignment_id == assignment_id,
        ExamResult.completed_at >= datetime.now() - timedelta(days=7)  # Last week
    ).order_by(ExamResult.completed_at.desc()).first()
    
    if recent_exam and recent_exam.study_hours_recommended:
        return recent_exam.study_hours_recommended
    
    # Fallback to user estimate or AI assessment
    user_assignment = db.query(UserAssignment).filter(...).first()
    if user_assignment.hours_estimated_user:
        return user_assignment.hours_estimated_user
    
    # Fallback to AI assessment
    assessment = db.query(AssignmentAssessment).filter(...).first()
    if assessment:
        return assessment.effort_hours_most
    
    return 3.0  # Default
```

### Option 3: Weight Multiple Sources

Combine exam results with other signals:

```python
def calculate_weighted_hours(
    exam_hours: float,
    assessment_hours: float,
    user_hours: float,
    hours_done: float
) -> float:
    """Combine multiple estimates with weights."""
    
    # Exam results get highest weight (most recent signal)
    weights = {
        'exam': 0.5,
        'assessment': 0.2,
        'user': 0.2,
        'progress_based': 0.1
    }
    
    progress_factor = max(1.0 - (hours_done / assessment_hours), 0.1)
    
    weighted = (
        exam_hours * weights['exam'] +
        assessment_hours * weights['assessment'] +
        user_hours * weights['user'] +
        (assessment_hours * progress_factor) * weights['progress_based']
    )
    
    return weighted
```

## Usage Example

### 1. Run Migration

```bash
cd /Users/mflodzinski/Projects/gradent
python scripts/add_exam_results_table.py
```

### 2. Test Exam Assessment

1. Generate a mock exam for an assignment
2. Answer questions
3. Click "Assess Exam"
4. Check database:

```python
from database.connection import get_db_session
from database.models import ExamResult

session = get_db_session()
results = session.query(ExamResult).all()
for r in results:
    print(f"{r.assignment.title}: {r.score}/{r.total_questions} ({r.percentage}%)")
    print(f"Recommended: {r.study_hours_recommended} hours")
```

### 3. Update Scheduler

Modify `workflows/scheduler/tools.py`:

```python
# Add this helper function
def get_exam_adjusted_hours(db: Session, user_id: int, assignment_id: int) -> Optional[float]:
    """Get study hours from most recent exam if available."""
    latest_exam = db.query(ExamResult).filter(
        ExamResult.user_id == user_id,
        ExamResult.assignment_id == assignment_id
    ).order_by(ExamResult.completed_at.desc()).first()
    
    return latest_exam.study_hours_recommended if latest_exam else None

# Update your scheduling logic to call this first
```

## Benefits

1. **Data-Driven**: Time estimates based on actual performance
2. **Personalized**: Adapts to individual student strengths/weaknesses
3. **Dynamic**: Updates as student knowledge improves
4. **Comprehensive**: Considers exam performance + AI assessment + user input

## Future Enhancements

1. **Trend Analysis**: Track improvement over multiple exams
2. **Topic Mapping**: Identify specific weak topics from wrong answers
3. **Adaptive Scheduling**: Allocate more time to difficult topics
4. **Confidence Scoring**: Weight recommendations by exam difficulty
5. **Spaced Repetition**: Schedule follow-up exams based on forgetting curve

## API Endpoints

### Assess Exam
```
POST /api/assess-exam
{
  "assignment_title": "Randomized Optimization",
  "course_name": "CS 7641",
  "questions": [...],
  "user_answers": {"1": "A", "2": "B", ...},
  "correct_answers": {"1": "A", "2": "C", ...}
}
```

### Get Exam Results (to be implemented)
```
GET /api/exam-results?user_id=1&assignment_id=5
```

## Database Queries

```python
# Get all exam results for a user
exams = db.query(ExamResult).filter(
    ExamResult.user_id == user_id
).order_by(ExamResult.completed_at.desc()).all()

# Get average performance across all exams
from sqlalchemy import func
avg_score = db.query(func.avg(ExamResult.percentage)).filter(
    ExamResult.user_id == user_id
).scalar()

# Get assignments that need more study (low exam scores)
weak_assignments = db.query(Assignment).join(ExamResult).filter(
    ExamResult.user_id == user_id,
    ExamResult.percentage < 70
).all()
```
