from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import func, select

from app.deps import CurrentUser, Session
from app.models import User
from app.schemas import LoginIn, TokenOut, UserOut
from app.security import create_access_token, login_throttle, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenOut)
async def login(data: LoginIn, request: Request, session: Session) -> TokenOut:
    client = request.client.host if request.client else "unknown"
    wait = login_throttle.seconds_until_allowed(client)
    if wait:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many failed sign-ins. Try again in {max(1, round(wait / 60))} min.",
            headers={"Retry-After": str(wait)},
        )

    user = await session.scalar(select(User).where(func.lower(User.email) == data.email.lower()))
    if not verify_password(data.password, user.password_hash if user else None):
        login_throttle.record_failure(client)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="That email and password don't match",
        )

    login_throttle.reset(client)
    return TokenOut(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser) -> User:
    return user
