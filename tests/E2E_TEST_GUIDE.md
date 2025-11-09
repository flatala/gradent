# E2E Context Update Flow Test Guide

## Overview

The `test_e2e_context_update_flow.py` test verifies the complete autonomous pipeline from LMS data ingestion through assignment assessment.

## What It Tests

This test simulates the real-world scenario where:
1. New assignments appear in Brightspace (LMS)
2. The system automatically detects and syncs them
3. Course materials are indexed for RAG
4. AI automatically assesses the assignment
5. Assessment is saved for scheduling

## Pipeline Flow

```
Brightspace (Mock) 
    ↓
Context Updater
    ↓
┌───────────────┴──────────────┐
│                              │
SQLite Database          ChromaDB Vector DB
(Structured Data)        (Content for RAG)
│                              │
└───────────────┬──────────────┘
    ↓
Assignment Assessment Workflow
    ↓
Database (Saved Assessment)
```

## Test Steps

### Step 1: Setup Test User
- Creates or retrieves test user (ID: 1)
- User: "Alex Student"

### Step 2: Context Update
- Calls `run_context_update(user_id=1)`
- Syncs from mock Brightspace:
  - Courses (e.g., "CS-4100 Artificial Intelligence")
  - Assignments (e.g., "Assignment 4: Reinforcement Learning")
  - Course materials (lecture notes, readings)

### Step 3: Verify Data Sync
**SQLite Database:**
- Courses stored with metadata
- Assignments with due dates
- Relationships maintained

**ChromaDB Vector Database:**
- Content chunked and embedded
- Metadata preserved for filtering
- Ready for semantic search

### Step 4: Test RAG Retrieval
- Queries vector DB for assignment-relevant content
- Retrieves top 3 most relevant chunks
- Displays sample context

### Step 5: Run Assessment Workflow
- Creates `AssignmentInfo` from database record
- Initializes `AssessmentState`
- Executes assessment workflow (async):
  1. **Initialize** - System prompt + assignment details
  2. **Analyze** - LLM reasoning about assignment
  3. **Generate Assessment** - Structured JSON output
  4. **Save to Database** - Persist assessment record

### Step 6: Verify Database Save
- Queries for latest assessment record
- Verifies `is_latest=True`
- Confirms all fields populated

### Step 7: Display Results
Shows comprehensive assessment summary:
- **Effort Estimates**: Optimistic, Most Likely, Pessimistic hours
- **Difficulty**: 1-5 scale rating
- **Risk Score**: 0-100 rating
- **Milestones**: Breakdown with hours per milestone
- **Prerequisites**: Required knowledge/skills
- **Deliverables**: What must be submitted
- **Dependencies**: External blockers

## Running the Test

```bash
# From project root
poetry run python tests/test_e2e_context_update_flow.py
```

### Prerequisites
- OPENAI_API_KEY in `.env` file
- Database initialized (auto-created if missing)
- Vector DB directory exists (auto-created)

## Expected Output

```
======================================================================
E2E TEST: Context Update → Assignment Assessment
======================================================================

This test simulates the autonomous pipeline when new assignments
are detected from the LMS (Brightspace).

🔧 Initializing configuration...
[OK] Configuration valid

======================================================================
STEP 1: Setup Test User
======================================================================
[OK] Using existing user: Alex Student (ID: 1)

======================================================================
STEP 2: Run Context Updater (Sync from Brightspace)
======================================================================
Fetching courses, assignments, and materials from LMS...

======================================================================
Context Updater: Syncing from Brightspace
======================================================================

1. Syncing courses...
   [OK] Synced 3 courses

2. Syncing assignments...
   [OK] Synced 5 assignments

3. Indexing course materials to vector DB...
   [OK] Indexed 25 content chunks

======================================================================
[OK] Context update complete!
======================================================================

[OK] Context update complete!
     Courses synced: 3
     Assignments synced: 5
     Content chunks indexed: 25

======================================================================
STEP 3: Verify Data Sync
======================================================================

📁 Normal Database (SQLite):
[OK] Found 3 courses in database
     - CS-4100: Artificial Intelligence
     - MATH-3310: Probability and Statistics
     - CS-3700: Networks and Distributed Systems
[OK] Found 5 assignments in database
     - Assignment 4: Reinforcement Learning (Due: 2025-11-25)
     - Problem Set 5: Markov Decision Processes (Due: 2025-11-20)
     - Project 2: Network Protocol Implementation (Due: 2025-12-01)

📚 Vector Database (ChromaDB):
[OK] Found 25 content chunks in vector database
     Source types: ['lecture_note', 'reading', 'assignment']

======================================================================
STEP 4: Test RAG Retrieval (Vector DB)
======================================================================

Querying for content related to: 'Assignment 4: Reinforcement Learning'

[OK] Retrieved 3 relevant chunks from vector DB

     Sample retrieved context:
     1. [lecture_note] Lecture 12: Reinforcement Learning
        Preview: This lecture covers the fundamentals of reinforcement learning, including...
     2. [reading] Chapter 17: Making Complex Decisions
        Preview: Reinforcement learning is about learning what to do—how to map situations...

======================================================================
STEP 5: Run Assignment Assessment Workflow
======================================================================

[Running] Assessing assignment: 'Assignment 4: Reinforcement Learning'
          Course: Artificial Intelligence
          Due: 2025-11-25

[OK] Assessment workflow completed successfully!
[OK] Structured assessment generated

======================================================================
STEP 6: Verify Assessment Saved to Database
======================================================================

[OK] Assessment saved to database (ID: 42)

======================================================================
ASSESSMENT SUMMARY
======================================================================

📊 Effort Estimates (PERT):
   • Optimistic:    8.0 hours
   • Most Likely:   12.0 hours
   • Pessimistic:   18.0 hours

📈 Difficulty & Risk:
   • Difficulty:    4.0/5
   • Risk Score:    65/100
   • AI Confidence: 0.85
   • Course Weight: 15.0%

🎯 Milestones (4):
   1. Implement Value Iteration (3.0h, 10 days before due)
   2. Implement Policy Iteration (3.0h, 8 days before due)
   3. Implement Q-Learning (4.0h, 5 days before due)
   4. Testing and Report Writing (2.0h, 1 days before due)

📚 Prerequisites (3):
   1. Markov Decision Processes
   2. Dynamic Programming
   3. NumPy/SciPy programming

📦 Deliverables (3):
   1. Python implementation of algorithms
   2. Test results and analysis
   3. Written report (3-4 pages)

======================================================================

======================================================================
✅ E2E TEST COMPLETE - ALL SYSTEMS OPERATIONAL
======================================================================

📋 Pipeline Verified:
   1. ✓ Context Updater synced from Brightspace
       └─ 3 courses, 5 assignments
   2. ✓ Data stored in SQLite database
   3. ✓ Content indexed in ChromaDB vector database
       └─ 25 chunks
   4. ✓ RAG retrieval working
       └─ Retrieved 3 relevant chunks
   5. ✓ Assignment assessment workflow executed
       └─ Analyzed: Assignment 4: Reinforcement Learning
   6. ✓ Assessment saved to database
       └─ Record ID: 42

🎉 All components working together successfully!
    The system can now autonomously detect, assess, and
    plan for new assignments from the LMS.
```

## Troubleshooting

### Test Fails at Context Update
- Check database write permissions
- Verify vector DB directory exists: `data/vector_db/`

### Test Fails at Assessment
- Verify OPENAI_API_KEY is valid
- Check OpenAI API rate limits
- Ensure sufficient API credits

### Database Already Exists
- Test uses existing data if present
- To start fresh: delete `study_assistant.db`

### Import Errors
- Run from project root directory
- Ensure poetry environment is activated

## Integration with Production

This test validates the code path used by:
- **Cron jobs** that check for new assignments
- **Webhooks** from LMS integration
- **Manual refresh** triggered by users
- **Background tasks** in ExecutorAgent

The same workflow tested here runs in production when the system
autonomously detects and processes new assignments.

## Related Files

- **Context Updater**: `context_updater/ingestion.py`
- **Brightspace Client**: `context_updater/brightspace_client.py`
- **Assessment Workflow**: `agents/task_agents/assignment_assessment/`
- **Database Models**: `database/models.py`
- **Vector DB**: `vector_db/ingestion.py`, `vector_db/retrieval.py`

## Next Steps

After this test passes, you can:
1. Run the chat agent: `poetry run python main.py`
2. Test executor agent: `agents/executor_agent/executor.py`
3. Set up cron jobs for automatic syncing
4. Configure Brightspace OAuth for real LMS data
