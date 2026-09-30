import pytest
import app.seed as seed

@pytest.fixture
def db(tmp_path, monkeypatch):
    # connect() resolves DB_PATH in the app.db namespace at call time.
    monkeypatch.setattr("app.db.DB_PATH", str(tmp_path / "t.db"))
    seed.init_db()
    yield
