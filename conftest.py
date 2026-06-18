"""Shared pytest fixtures for Spendly.

The whole suite runs against a throwaway SQLite file (one per test) by
pointing the SPENDLY_DB env var at a tmp path before any DB connection is
opened. get_db() reads SPENDLY_DB at call time, so the real spendly.db is
never touched.
"""

import pytest


@pytest.fixture
def app(monkeypatch, tmp_path):
    db_path = tmp_path / "test_spendly.db"
    monkeypatch.setenv("SPENDLY_DB", str(db_path))

    # Imported here (after the env var is set) so the module-level
    # init_db()/seed_db() in app.py run against the temp database.
    import app as app_module

    app_module.app.config.update(TESTING=True)
    with app_module.app.app_context():
        app_module.init_db()
        app_module.seed_db()
    return app_module.app
