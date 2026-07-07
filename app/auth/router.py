"""FastAPI auth endpoints + the `require_user` dependency used to protect routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel

from app.auth.service import AuthError, AuthService, AuthStore
from app.config import Settings


class LoginBody(BaseModel):
    username: str
    password: str


class RefreshBody(BaseModel):
    refresh_token: str


def build_auth(settings: Settings, service: AuthService | None = None) -> tuple[APIRouter, object, AuthService]:
    """Return (router, require_user_dependency, service)."""
    service = service or AuthService(AuthStore(settings.auth_path))
    router = APIRouter(prefix="/api/auth", tags=["auth"])

    def require_user(authorization: str = Header(default="")) -> str:
        """FastAPI dependency: validate the Bearer access token → username."""
        if not authorization.startswith("Bearer "):
            raise HTTPException(401, "missing bearer token")
        try:
            return service.verify_access(authorization[7:])
        except AuthError as e:
            raise HTTPException(401, str(e)) from e

    @router.get("/status")
    def status():
        # tells the login page whether an account exists yet
        return {"configured": service.store.is_configured(), "user": service.store.username}

    @router.post("/login")
    def login(body: LoginBody, request: Request):
        client_key = request.client.host if request.client else "default"
        try:
            return service.login(body.username, body.password, client_key)
        except AuthError as e:
            raise HTTPException(401, str(e)) from e

    @router.post("/refresh")
    def refresh(body: RefreshBody):
        try:
            return service.refresh(body.refresh_token)
        except AuthError as e:
            raise HTTPException(401, str(e)) from e

    @router.post("/logout")
    def logout(_user: str = Depends(require_user)):
        # Stateless JWT: logout is client-side (drop the tokens). Endpoint exists
        # for symmetry and to confirm the token was valid.
        return {"ok": True}

    @router.get("/me")
    def me(user: str = Depends(require_user)):
        return {"user": user}

    return router, require_user, service
