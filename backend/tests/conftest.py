"""pytest 配置：用临时数据库，避免动开发库。"""
import os
import tempfile
from pathlib import Path

# 每次测试进程使用独立目录，退出时连同 WAL/SHM 一起清理。
_TEST_DIR = tempfile.TemporaryDirectory(prefix="zhiyu-tests-")
TEST_DB = Path(_TEST_DIR.name) / "app.db"

os.environ["APP_DB_PATH"] = str(TEST_DB)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client
