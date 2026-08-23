from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base that Alembic autogenerate compares the live schema against.

    Empty until phase 2 introduces the tables in section 6 of the build spec.
    """
