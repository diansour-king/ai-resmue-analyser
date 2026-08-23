from datetime import timedelta

from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select

from ..db import utcnow
from ..deps import CurrentUser, DbSession
from ..models import LoginToken, Session, User
from ..observability import log
from ..security import hash_token, new_token
from ..settings import get_settings

router = APIRouter(prefix="/v1/auth", tags=["auth"])


class SignUpRequest(BaseModel):
    email: EmailStr
    display_name: str | None = Field(default=None, max_length=120)


class LoginRequest(BaseModel):
    email: EmailStr


class VerifyRequest(BaseModel):
    token: str


class LinkIssued(BaseModel):
    """The link is only ever returned in development, where there is no mail server."""

    sent: bool
    login_url: str | None = None


class Identity(BaseModel):
    user_id: str
    email: str
    display_name: str | None
    onboarded: bool


@router.post("/signup", status_code=status.HTTP_202_ACCEPTED)
async def sign_up(payload: SignUpRequest, session: DbSession) -> LinkIssued:
    user = await _user_by_email(session, payload.email)
    if user is None:
        user = User(email=payload.email.lower(), display_name=payload.display_name)
        session.add(user)
        await session.flush()
        log("signup_created", user_id=str(user.id))
    elif payload.display_name and not user.display_name:
        user.display_name = payload.display_name
    return await _issue_link(session, user)


@router.post("/login", status_code=status.HTTP_202_ACCEPTED)
async def log_in(payload: LoginRequest, session: DbSession) -> LinkIssued:
    """Always reports success.

    Answering differently for a known and an unknown address turns this endpoint into a
    test for whether a given person has an account here, which is not ours to disclose.
    """
    user = await _user_by_email(session, payload.email)
    if user is None:
        log("login_requested_unknown_address")
        return LinkIssued(sent=True)
    return await _issue_link(session, user)


@router.post("/verify")
async def verify(payload: VerifyRequest, response: Response, session: DbSession) -> Identity:
    settings = get_settings()
    result = await session.execute(
        select(LoginToken).where(LoginToken.token_hash == hash_token(payload.token))
    )
    token = result.scalar_one_or_none()
    if token is None or token.consumed_at is not None or token.expires_at < utcnow():
        raise _invalid_link()

    token.consumed_at = utcnow()
    secret, token_hash = new_token()
    session.add(
        Session(
            user_id=token.user_id,
            token_hash=token_hash,
            expires_at=utcnow() + timedelta(hours=settings.session_ttl_hours),
        )
    )
    user = await session.get(User, token.user_id)
    if user is None:
        raise _invalid_link()
    await session.commit()

    response.set_cookie(
        settings.session_cookie_name,
        secret,
        max_age=settings.session_ttl_hours * 3600,
        httponly=True,
        samesite="lax",
        secure=not settings.expose_login_links,
        path="/",
    )
    log("session_started", user_id=str(user.id))
    return _identity(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def log_out(request: Request, response: Response, session: DbSession) -> None:
    settings = get_settings()
    secret = request.cookies.get(settings.session_cookie_name)
    if secret:
        result = await session.execute(
            select(Session).where(Session.token_hash == hash_token(secret))
        )
        stored = result.scalar_one_or_none()
        if stored is not None:
            stored.revoked_at = utcnow()
            await session.commit()
    response.delete_cookie(settings.session_cookie_name, path="/")


@router.get("/me")
async def me(user: CurrentUser) -> Identity:
    return _identity(user)


class OnboardingRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=120)


@router.post("/onboarding")
async def complete_onboarding(
    payload: OnboardingRequest, user: CurrentUser, session: DbSession
) -> Identity:
    """The whole of onboarding: a name to greet them by.

    Nothing else is collected because nothing else is used. A profile system with fields no
    screen reads would be work that never pays for itself.
    """
    user.display_name = payload.display_name
    user.onboarded_at = utcnow()
    await session.commit()
    return _identity(user)


async def _user_by_email(session: DbSession, email: str) -> User | None:
    result = await session.execute(select(User).where(User.email == email.lower()))
    return result.scalar_one_or_none()


async def _issue_link(session: DbSession, user: User) -> LinkIssued:
    settings = get_settings()
    secret, token_hash = new_token()
    session.add(
        LoginToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=utcnow() + timedelta(minutes=settings.login_token_ttl_minutes),
        )
    )
    await session.commit()
    log("login_link_issued", user_id=str(user.id))
    if settings.expose_login_links:
        return LinkIssued(sent=True, login_url=f"/auth/verify?token={secret}")
    return LinkIssued(sent=True)


def _identity(user: User) -> Identity:
    return Identity(
        user_id=str(user.id),
        email=user.email,
        display_name=user.display_name,
        onboarded=user.onboarded_at is not None,
    )


def _invalid_link() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={"code": "invalid_link", "message": "That sign-in link is no longer valid."},
    )
