# Quick Reference: E2E Executor Test

## Run the Test

```bash
python tests/test_e2e_executor_context_update.py
```

## What It Tests

✅ `ExecutorAgent.run_context_update_and_assess()` - your production method  
✅ LLM agent autonomously orchestrates the workflow  
✅ Context update syncs from Brightspace  
✅ Assignment assessment workflow  
✅ Database persistence  

## Test Validates

1. **Context Update**: Syncs courses/assignments from LMS
2. **Unassessed Detection**: Finds assignments without assessments
3. **Assessment Creation**: Analyzes effort, difficulty, creates milestones
4. **Database Updates**: All data persisted correctly
5. **Workflow Success**: No errors, returns success=True

## Expected Duration

⏱️ **30-60 seconds** (includes LLM API calls)

## Success Criteria

```
[✓] Context update synced data
[✓] Assignments exist in database
[✓] New assessments created
[✓] Executor workflow succeeded
```

## Files Created

```
tests/
├── test_e2e_executor_context_update.py       ← Main test (run this)
├── E2E_EXECUTOR_TEST_README.md               ← Full documentation
├── E2E_EXECUTOR_TEST_SUMMARY.md              ← Overview
└── E2E_EXECUTOR_QUICK_REFERENCE.md           ← This file
```

## Troubleshooting

**Test fails?** Check `E2E_EXECUTOR_TEST_README.md` → Troubleshooting section

**Want more details?** Read `E2E_EXECUTOR_TEST_SUMMARY.md`

**Need help?** Look at the test output - it shows each step clearly
