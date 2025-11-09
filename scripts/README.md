# Setup Scripts

This directory contains scripts for setting up and managing the Gradent development environment.

## Quick Start

The easiest way to set up everything is to use the unified setup script:

```bash
# From the project root
poetry run python scripts/setup_all.py

# Or use the convenience script
bash setup.sh
```

This will set up:
- SQL database with proper schema
- Mock data (users, courses, assignments)
- Vector database with assignment documents
- Sample suggestions

### Options

```bash
# Full reset (clear all existing data)
poetry run python scripts/setup_all.py --reset

# Non-interactive full reset
poetry run python scripts/setup_all.py --full-reset
```

## Individual Scripts

If you need to run specific setup steps independently:

### 1. `setup_all.py` ⭐ **RECOMMENDED**

**Purpose:** Unified setup script that runs all setup steps in the correct order.

**What it does:**
- Initializes SQL database schema
- Populates mock data (users, courses, assignments)
- Creates sample suggestions
- Sets up vector database with assignment documents
- Verifies all components

**Usage:**
```bash
# Interactive setup (asks for confirmation)
poetry run python scripts/setup_all.py

# Full reset without prompts
poetry run python scripts/setup_all.py --reset

# Quick setup (preserves existing data if possible)
poetry run python scripts/setup_all.py --no-reset
```

---

### 2. `migrate_database.py`

**Purpose:** Migrate database schema and existing data.

**What it does:**
- Creates/updates database tables
- Migrates existing Assignment data to UserAssignment table
- Ensures all relationships are properly set up

**Usage:**
```bash
poetry run python scripts/migrate_database.py
```

**When to use:**
- After pulling schema changes from git
- When database structure has been updated
- First time setup (but `setup_all.py` is easier)

---

### 3. `setup_mock_data.py`

**Purpose:** Populate database with test data for development.

**What it does:**
- Creates a test user (Test Student)
- Creates 3 sample courses (RL, ML, CV)
- Creates 5 assignments with varying deadlines
- Creates user-assignment relationships
- Creates sample suggestions

**Usage:**
```bash
poetry run python scripts/setup_mock_data.py
```

**When to use:**
- Need fresh test data
- Want to reset data without affecting vector DB
- Testing database operations

---

### 4. `setup_vector_db.py`

**Purpose:** Initialize and populate the vector database with assignment documents.

**What it does:**
- Sets up ChromaDB vector store
- Ingests mock assignment documents
- Creates embeddings for semantic search
- Verifies vector DB with sample queries

**Usage:**
```bash
# With reset confirmation
poetry run python scripts/setup_vector_db.py

# Keep existing data
poetry run python scripts/setup_vector_db.py --no-reset
```

**When to use:**
- Setting up RAG (Retrieval-Augmented Generation)
- Testing semantic search functionality
- Updating vector embeddings after document changes

---

### 5. `setup_mock_suggestions.py`

**Purpose:** Create sample suggestion notifications.

**What it does:**
- Clears existing suggestions for user
- Creates 3 sample suggestions with different priorities
- Links suggestions to assignments

**Usage:**
```python
# Usually imported by other scripts
from scripts.setup_mock_suggestions import populate_suggestions
populate_suggestions(user_id=1)
```

**When to use:**
- Testing notification system
- Demonstrating suggestion features
- Usually called by `setup_all.py`

---

## Common Workflows

### Fresh Development Setup
```bash
# One command to set up everything
bash setup.sh
```

### Reset Everything
```bash
poetry run python scripts/setup_all.py --reset
```

### Update Only SQL Data
```bash
poetry run python scripts/setup_mock_data.py
```

### Update Only Vector DB
```bash
poetry run python scripts/setup_vector_db.py
```

### Just Migrate Schema (No Data Changes)
```bash
poetry run python scripts/migrate_database.py
```

## Verification

After running any setup script, verify your setup:

```bash
# Check database contents
poetry run python verify_db.py

# Run tests
poetry run pytest tests/

# Check vector DB
poetry run python scripts/setup_vector_db.py
# Then choose 'y' for verification queries
```

## Files Created

After successful setup, you should see:

- `data/study_assistant.db` - SQLite database
- `data/chroma_db/` - Vector database directory
- Log files in `logs/` directory

## Troubleshooting

### "No module named X"
```bash
# Reinstall dependencies
poetry install
```

### "Database locked" error
```bash
# Close any applications accessing the database
# Then re-run the setup script
```

### Vector DB errors
```bash
# Reset vector DB completely
rm -rf data/chroma_db/
poetry run python scripts/setup_vector_db.py
```

### Import errors
```bash
# Make sure you're in the project root
cd /path/to/gradent
poetry run python scripts/setup_all.py
```

## Development Notes

- All scripts add the project root to `sys.path` for imports
- Scripts are safe to run multiple times (idempotent)
- The `--reset` flag clears existing data before setup
- Mock data IDs are consistent across runs (useful for testing)

## Need Help?

Check the main project README or documentation in `docs/` directory.
