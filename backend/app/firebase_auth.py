"""Firebase ID-token verification for authenticated VaaniSetu API routes."""
import json
import os
from functools import lru_cache
from typing import Any

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

security = HTTPBearer(auto_error=False)


@lru_cache(maxsize=1)
def _firebase_app():
    raw = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON", "").strip()
    if not raw:
        raise RuntimeError("FIREBASE_SERVICE_ACCOUNT_JSON is not configured")
    try:
        service_account = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("FIREBASE_SERVICE_ACCOUNT_JSON is not valid JSON") from exc

    import firebase_admin
    from firebase_admin import credentials

    try:
        return firebase_admin.get_app()
    except ValueError:
        return firebase_admin.initialize_app(credentials.Certificate(service_account))


async def require_firebase_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict[str, Any]:
    if credentials is None or credentials.scheme.lower() != "bearer" or not credentials.credentials:
        raise HTTPException(status_code=401, detail="A valid Firebase sign-in is required.", headers={"WWW-Authenticate": "Bearer"})
    try:
        app = _firebase_app()
    except (RuntimeError, ValueError):
        raise HTTPException(status_code=503, detail="Firebase server authentication is not configured. Contact the VaaniSetu administrator.")

    from firebase_admin import auth
    try:
        return auth.verify_id_token(credentials.credentials, app=app, check_revoked=True)
    except (auth.InvalidIdTokenError, auth.ExpiredIdTokenError, auth.RevokedIdTokenError, auth.UserDisabledError):
        raise HTTPException(status_code=401, detail="Your sign-in has expired. Please sign in again.", headers={"WWW-Authenticate": "Bearer"})
    except Exception:
        raise HTTPException(status_code=401, detail="Firebase sign-in could not be verified.", headers={"WWW-Authenticate": "Bearer"})
