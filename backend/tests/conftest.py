import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture()
def temp_db_path(tmp_path):
    return tmp_path / "video_workbench_test.db"


@pytest.fixture()
def temp_projects_root(tmp_path):
    root = tmp_path / "video_projects"
    root.mkdir()
    return root


@pytest.fixture()
def sqlite_conn(temp_db_path):
    conn = sqlite3.connect(temp_db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()
