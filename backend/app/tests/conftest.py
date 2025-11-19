import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.crud.user import create_user
from app.schemas.auth import UserCreate
from app.db.models import UserRole

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="function")
def db() -> Session:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db_session = TestingSessionLocal()
    try:
        # Create users for testing
        create_user(db=db_session, user=UserCreate(username="admin", password="password", role=UserRole.admin))
        create_user(db=db_session, user=UserCreate(username="operator", password="password", role=UserRole.operator))
        create_user(db=db_session, user=UserCreate(username="viewer", password="password", role=UserRole.viewer))
        yield db_session
    finally:
        db_session.close()
