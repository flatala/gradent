"""Populate the suggestions table with demo-friendly rows."""
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path so we can import from root modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.connection import get_db_session, init_db
from database.models import Suggestion, SuggestionStatus


SAMPLE_SUGGESTIONS = [
    {
        "title": "Kick off MDP Implementation",
        "message": "Block 90 minutes to read the MDP chapter and list milestones for value/policy iteration.",
        "category": "deadline_reminder",
        "priority": "high",
        "suggested_time": datetime.utcnow() + timedelta(minutes=2),
        "tags": ["mdp", "rl"],
        "linked_assignments": [1],
    },
    {
        "title": "Resource review: Hybrid Images",
        "message": "Skim the hybrid-images doc to refresh Gaussian/Laplacian pyramids before coding.",
        "category": "resource_recommendation",
        "priority": "medium",
        "suggested_time": datetime.utcnow() + timedelta(minutes=5),
        "tags": ["cv"],
        "linked_assignments": [5],
    },
    {
        "title": "Plan Supervised Learning sessions",
        "message": "Schedule 2-3 focused blocks to make progress on preprocessing and experiments.",
        "category": "schedule_gap",
        "priority": "medium",
        "suggested_time": datetime.utcnow() + timedelta(minutes=8),
        "tags": ["ml"],
        "linked_assignments": [3],
    },
]


def populate_suggestions(user_id: int = 1) -> None:
    """Insert demo suggestions for the specified user."""
    init_db()
    with get_db_session() as db:
        # Clear existing suggestions for a clean demo
        db.query(Suggestion).delete()

    with get_db_session() as db:
        for item in SAMPLE_SUGGESTIONS:
            suggestion = Suggestion(
                user_id=user_id,
                title=item["title"],
                message=item["message"],
                category=item["category"],
                priority=item["priority"],
                suggested_time=item["suggested_time"],
                suggested_time_text=None,
                linked_assignments=item.get("linked_assignments", []),
                linked_events=[],
                tags=item.get("tags", []),
                sources=[],
                channel_config={"discord": True},
                status=SuggestionStatus.PENDING,
            )
            db.add(suggestion)

    print(f"✓ Inserted {len(SAMPLE_SUGGESTIONS)} demo suggestions for user_id={user_id}")


if __name__ == "__main__":
    populate_suggestions()

