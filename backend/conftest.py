import pytest

from app import seed
import app.db as dbmod
import app.config as cfg


@pytest.fixture
def temp_db(monkeypatch, tmp_path):
    # connect() looks up DB_PATH in the app.db namespace; patch both bindings for safety.
    path = tmp_path / "test.db"
    monkeypatch.setattr(dbmod, "DB_PATH", path)
    monkeypatch.setattr(cfg, "DB_PATH", path)
    seed.init_db()
    return path
