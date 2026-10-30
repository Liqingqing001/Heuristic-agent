"""pytest 配置：用临时数据库，避免动开发库。"""
import os
import tempfile
from pathlib import Path

TEST_DB = Path(tempfile.gettempdir()) / "zhiyu_test.db"
for suffix in ("", "-wal", "-shm"):
    candidate = Path(str(TEST_DB) + suffix)
    if candidate.exists():
        candidate.unlink()

os.environ["APP_DB_PATH"] = str(TEST_DB)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client
