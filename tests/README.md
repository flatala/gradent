# Tests

This directory contains all test scripts for the study assistant application.

## Test Files

### `test_vector_simple.py`
Quick verification test for vector database functionality.

**What it tests:**
- Vector store initialization
- Document ingestion and chunking
- Collection statistics
- Semantic search retrieval

**Run:**
```bash
poetry run python tests/test_vector_simple.py
```

**Requirements:** OPENAI_API_KEY in `.env`

---

### `test_assessment.py`
Test the assignment assessment workflow with mock data.

**What it tests:**
- Database initialization
- Assessment workflow execution
- LLM-based analysis and structured output
- Database storage of assessments

**Run:**
```bash
poetry run python tests/test_assessment.py
```

**Requirements:** OPENAI_API_KEY in `.env`

---

### `test_e2e_rag.py`
Complete end-to-end test of the RAG pipeline.

**What it tests:**
- Normal database setup with mock data
- Vector database population
- RAG context retrieval
- Assessment workflow with retrieved context
- Database verification

**Run:**
```bash
poetry run python tests/test_e2e_rag.py
```

**Requirements:** OPENAI_API_KEY in `.env`

**Output:** Complete workflow demonstration showing:
1. Database setup (SQLite + ChromaDB)
2. RAG retrieval from vector DB
3. Assessment generation with context
4. Results saved to normal database

---

## Running All Tests

```bash
# Run tests in sequence
poetry run python tests/test_vector_simple.py
poetry run python tests/test_assessment.py  
poetry run python tests/test_e2e_rag.py
```

## Test Data

All tests use mock data:
- **Normal DB**: 1 user, 3 courses, 5 assignments
- **Vector DB**: 3 assignment documents (25 chunks total)

Mock data is automatically created when tests run.

## Troubleshooting

### Import Errors
Tests add the parent directory to `sys.path` automatically. If you still get import errors:
```bash
# Run from project root
cd /path/to/gradent
poetry run python tests/test_name.py
```

### OpenAI API Errors
Make sure your `.env` file contains:
```
OPENAI_API_KEY=your-key-here
```

### Database Locked
If SQLite database is locked, close any database viewers and try again.

### ChromaDB Warnings
Telemetry warnings from ChromaDB can be safely ignored:
```
Failed to send telemetry event...
```

These don't affect functionality.
