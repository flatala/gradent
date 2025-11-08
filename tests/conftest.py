import importlib
import os
import sys
from pathlib import Path
from typing import Generator

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture()
def temp_database(tmp_path, monkeypatch) -> Generator[Path, None, None]:
    """Create a temporary SQLite database and reload connection module."""
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_PATH", str(db_path))

    # Reload database.connection so it picks up the new env variable
    from database import connection as connection_module

    importlib.reload(connection_module)
    connection_module.init_db()

    yield db_path

    # Cleanup: remove env, reload to default state
    monkeypatch.delenv("DATABASE_PATH", raising=False)
    importlib.reload(connection_module)

