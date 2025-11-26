"""Database initialization entrypoint."""

from app.db.utils import seed_with_new_session


def init_db() -> None:
    """Create tables and seed default data using a fresh session."""
    seed_with_new_session()


if __name__ == "__main__":
    init_db()
