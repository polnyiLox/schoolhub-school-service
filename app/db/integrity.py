from sqlalchemy.exc import IntegrityError


def get_constraint_name(error: IntegrityError) -> str | None:
    """Extract a PostgreSQL constraint name through SQLAlchemy/asyncpg wrappers."""
    candidates = (error.orig, getattr(error.orig, "__cause__", None))
    for candidate in candidates:
        constraint_name = getattr(candidate, "constraint_name", None)
        if isinstance(constraint_name, str):
            return constraint_name
    return None
