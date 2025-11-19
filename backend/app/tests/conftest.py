from __future__ import annotations

from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.deps import get_current_user
from app.core.time import utcnow
from app.db.base import Base
from app.db.session import get_db
from app.devices import models as _device_models  # noqa: F401
from app.jobs import models as _job_models  # noqa: F401
from app.jobs.models import User
from app.main import app
from app.config_backup import models as _config_models  # noqa: F401
from app.compliance import models as _compliance_models  # noqa: F401

SQLALCHEMY_DATABASE_URL = "sqlite+pysqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


@pytest.fixture()
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            db_session.rollback()

    app.dependency_overrides[get_db] = override_get_db

    admin_user = User(username="tester", hashed_password="x", role="admin", created_at=utcnow())
    db_session.add(admin_user)
    db_session.commit()

    def override_current_user():
        return admin_user

    app.dependency_overrides[get_current_user] = override_current_user

    test_client = TestClient(app)
    yield test_client

    app.dependency_overrides.clear()
