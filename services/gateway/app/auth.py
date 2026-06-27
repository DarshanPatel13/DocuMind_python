"""Login endpoint logic + the `get_current_user` dependency.

Every proxied `/api/*` route depends on `get_current_user`, so an invalid or
missing token is rejected at the edge with 401 before any internal service is
even contacted.
"""
from __future__ import annotations

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from documind_contracts import LoginRequest, TokenResponse

from app.db import get_user
from app.security import create_access_token, decode_access_token, verify_password

_bearer = HTTPBearer(auto_error=False)


async def login(body: LoginRequest) -> TokenResponse:
    user = await get_user(body.username)
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    return TokenResponse(access_token=create_access_token(user.username))


async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str:
    if creds is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        return decode_access_token(creds.credentials)
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
