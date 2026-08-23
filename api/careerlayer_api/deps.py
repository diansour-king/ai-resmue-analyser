from collections.abc import AsyncIterator
from datetime import datetime
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .db import utcnow
from .models import Session, User
from .security import hash_token
from .settings import get_settings


async def db_session(request: Request) -> AsyncIterator[AsyncSession]:
    factory = request.app.state.session_factory
    async with factory() as session:
        yield session


DbSession = Annotated[AsyncSession, Depends(db_session)]


async def current_user(request: Request, session: DbSession) -> User:
    """Resolve the signed-in user, or refuse the request.

    Every resume route depends on this. Ownership is then checked again per row, because
    being signed in is not the same as being allowed to read a particular document.
    """
    secret = request.cookies.get(get_settings().session_cookie_name)
    if not secret:
        raise _unauthenticated()

    result = await session.execute(select(Session).where(Session.token_hash == hash_token(secret)))
    stored = result.scalar_one_or_none()
    if stored is None or stored.revoked_at is not None or _expired(stored.expires_at):
        raise _unauthenticated()

    user = await session.get(User, stored.user_id)
    if user is None:
        raise _unauthenticated()
    return user


CurrentUser = Annotated[User, Depends(current_user)]


def _expired(moment: datetime) -> bool:
    return moment < utcnow()


def _unauthenticated() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": "unauthenticated", "message": "Sign in to continue."},
    )
