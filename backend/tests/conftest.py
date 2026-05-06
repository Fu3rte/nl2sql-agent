import os
import sys
import pytest

# Ensure backend root is on path so imports like 'from app.xxx' work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture(autouse=True)
def use_test_db(monkeypatch):
    """Force tests to use a temp database instead of production ecommerce.db."""
    import tempfile
    import app.database as db_mod

    fd, tmp_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    monkeypatch.setattr(db_mod, "DB_PATH", tmp_path)
    db_mod.init_db()
    yield
    try:
        os.unlink(tmp_path)
    except OSError:
        pass


@pytest.fixture
def client():
    """Async test client for FastAPI app."""
    from httpx import ASGITransport, AsyncClient
    from main import app

    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")
