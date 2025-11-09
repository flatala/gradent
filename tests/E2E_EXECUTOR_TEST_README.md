# E2E Test: ExecutorAgent Context Update & Assessment

## Overview

This test verifies the `ExecutorAgent.run_context_update_and_assess()` method, which autonomously orchestrates:

1. **Context Update**: Syncs courses and assignments from Brightspace (mock LMS)
2. **Get Unassessed Assignments**: Identifies assignments without assessments
3. **Assignment Assessment**: Analyzes difficulty, effort, and creates milestones
4. **Database Updates**: Stores all data in SQLite database

## What Makes This Test Unique

This test is different from other E2E tests because:

- **Tests the ExecutorAgent**: Uses the autonomous executor agent (not chat agent)
- **LLM Orchestration**: The LLM agent decides which tools to call and in what order
- **Autonomous Workflow**: No user interaction - fully autonomous background task
- **Tool Usage Validation**: Verifies the agent uses tools correctly (run_context_update, get_unassessed_assignments, assess_assignment)

## Prerequisites

1. **Environment Variables**: Ensure `.env` is configured with:
   - `OPENAI_API_KEY` or other LLM provider credentials
   - `DATABASE_PATH` (optional, defaults to `gradent.db`)
   - `BRIGHTSPACE_CLIENT_ID` and `BRIGHTSPACE_CLIENT_SECRET` (for real API, or will use mock)

2. **Database**: The test creates a test user automatically

3. **Dependencies**: Install with `pip install -r requirements.txt` or `uv pip install -r requirements.txt`

## Running the Test

### Quick Run

```bash
python tests/test_e2e_executor_context_update.py
```

### With pytest

```bash
pytest tests/test_e2e_executor_context_update.py -v
```

### With verbose logging

```bash
LOGLEVEL=DEBUG python tests/test_e2e_executor_context_update.py
```

## Test Flow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Setup Test User                                          │
│    - Create/verify test user in database                    │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. Get Initial Database State                               │
│    - Count courses, assignments, assessments                │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. Initialize ExecutorAgent                                 │
│    - Load configuration and LLM                             │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. Run Executor Workflow                                    │
│    executor.run_context_update_and_assess()                 │
│                                                              │
│    LLM Agent orchestrates:                                  │
│    a) run_context_update(user_id=1)                         │
│    b) get_unassessed_assignments(user_id=1)                 │
│    c) assess_assignment(...) for each unassessed            │
│    d) (optional) run_scheduler_workflow(...)                │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. Check Executor Result                                    │
│    - Verify success=True                                    │
│    - Log duration and output                                │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 6. Verify Database Updates                                  │
│    - Check courses/assignments were synced                  │
│    - Verify assessments were created                        │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 7. Validate Assessment Details                              │
│    - Effort estimates exist                                 │
│    - Difficulty rating present                              │
│    - Milestones created                                     │
└─────────────────────────────────────────────────────────────┘
```

## Expected Output

```
======================================================================
E2E TEST: ExecutorAgent.run_context_update_and_assess()
======================================================================

STEP 1: Setting up test user...
[OK] Using existing user: Test Student (ID: 1)

STEP 2: Getting initial database state...
[INFO] Initial state:
       - Courses: 3
       - Assignments: 5
       - Assessments: 2

STEP 3: Initializing ExecutorAgent...
[OK] ExecutorAgent initialized

STEP 4: Running ExecutorAgent.run_context_update_and_assess()...
[INFO] This will:
       1. Run context update (sync from Brightspace)
       2. Get unassessed assignments
       3. Assess at least one assignment
       4. Optionally schedule study sessions

[WAIT] Executor agent is working (this may take 30-60 seconds)...

STEP 5: Checking executor result...
[OK] Executor workflow completed successfully
[INFO] Duration: 45231ms
[INFO] Agent output:
Successfully completed context update and assessment workflow...

STEP 6: Verifying database updates...
[INFO] Final state:
       - Courses: 3 (change: +0)
       - Assignments: 5 (change: +0)
       - Assessments: 3 (change: +1)

STEP 7: Verifying assignment assessment...
[OK] Found assessment for: Machine Learning Project
     - Effort (most likely): 8.0 hours
     - Difficulty: 3/5
     - Risk Score: 45/100
     - Milestones: 4

======================================================================
FINAL VALIDATION
======================================================================
[✓] Context update synced data
[✓] Assignments exist in database
[✓] New assessments created
[✓] Executor workflow succeeded

======================================================================
TEST PASSED: All checks passed! ✓
======================================================================
```

## What the Test Validates

✅ **ExecutorAgent Initialization**: Agent loads correctly with LLM configuration

✅ **Autonomous Tool Usage**: LLM agent uses the right tools in correct order

✅ **Context Update**: New courses/assignments synced from Brightspace

✅ **Assignment Detection**: Unassessed assignments are identified

✅ **Assessment Workflow**: At least one assignment gets assessed with:
   - Effort estimates (low, most likely, high)
   - Difficulty rating (1-5)
   - Risk score (0-100)
   - Milestones breakdown

✅ **Database Persistence**: All data stored correctly in SQLite

✅ **Error Handling**: Workflow completes successfully or reports errors

## Troubleshooting

### Test fails with "No assignment assessment found"

**Cause**: The LLM agent may not have called `assess_assignment()` tool

**Solutions**:
- Check logs for agent tool calls
- Verify LLM has access to tools (check `agents/shared/workflow_tools.py`)
- Ensure assignments exist after context update

### Test times out or takes very long

**Cause**: LLM API calls can be slow, especially with complex prompts

**Solutions**:
- Expected duration: 30-60 seconds
- Check LLM provider status
- Try with a faster model (e.g., GPT-4o-mini instead of GPT-4)

### "No courses synced" or "No assignments synced"

**Cause**: Context updater may be using mock data or Brightspace API unavailable

**Solutions**:
- This is OK for testing! The test can pass with existing data
- Check `context_updater/brightspace_client.py` for mock vs real API
- Verify Brightspace credentials if using real API

### Import errors or module not found

**Cause**: Python path or dependencies issue

**Solutions**:
```bash
# Reinstall dependencies
pip install -r requirements.txt

# Run from project root
cd /path/to/gradent
python tests/test_e2e_executor_context_update.py
```

## Related Tests

- `test_e2e_context_update_flow.py`: Tests context update → assessment (manual orchestration)
- `test_executor.py`: Tests other ExecutorAgent methods
- `test_assessment.py`: Tests assignment assessment workflow in isolation

## Notes

- **Auto-scheduling disabled**: The test sets `auto_schedule=False` for faster execution
- **Test data**: Uses existing database or creates mock user/courses
- **Non-destructive**: Test doesn't delete existing data
- **Idempotent**: Can run multiple times safely
