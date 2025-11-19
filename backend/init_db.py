"""Database initialization script."""

from app.db import Base, engine, SessionLocal, User
from app.core.auth import get_password_hash


def init_db() -> None:
    """Initialize database - create tables and default admin user."""
    # Create tables
    Base.metadata.create_all(bind=engine)
    print("Database tables created")
    
    # Create default admin user if not exists
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            admin = User(
                username="admin",
                hashed_password=get_password_hash("admin123"),
                role="admin",
                is_active=True,
            )
            db.add(admin)
            db.commit()
            print("Default admin user created (username: admin, password: admin123)")
        else:
            print("Admin user already exists")
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
