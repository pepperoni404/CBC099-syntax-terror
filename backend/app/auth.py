import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
import bcrypt
import jwt
from fastapi import Depends, Header
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models import Agent
from app.utils.validators import AppException


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception:
        return False


def create_access_token(agent_id: str, agent_name: str) -> tuple[str, int]:
    expires_delta = timedelta(hours=settings.JWT_EXPIRY_HOURS)
    expire_time = datetime.now(timezone.utc) + expires_delta
    expires_in_seconds = int(expires_delta.total_seconds())

    payload = {
        "sub": str(agent_id),
        "name": agent_name,
        "exp": expire_time,
        "iat": datetime.now(timezone.utc),
    }

    token = jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")
    return token, expires_in_seconds


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise AppException(
            status_code=401,
            code="TOKEN_EXPIRED",
            message="Authentication token has expired",
        )
    except jwt.PyJWTError:
        raise AppException(
            status_code=401,
            code="NOT_AUTHENTICATED",
            message="Authentication required",
        )


def get_current_agent(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> Agent:
    if not authorization:
        raise AppException(
            status_code=401,
            code="NOT_AUTHENTICATED",
            message="Authentication required",
        )

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise AppException(
            status_code=401,
            code="NOT_AUTHENTICATED",
            message="Authentication required",
        )

    token = parts[1]
    payload = decode_access_token(token)

    agent_id_str = payload.get("sub")
    if not agent_id_str:
        raise AppException(
            status_code=401,
            code="NOT_AUTHENTICATED",
            message="Authentication required",
        )

    try:
        agent_uuid = uuid.UUID(agent_id_str)
    except ValueError:
        raise AppException(
            status_code=401,
            code="NOT_AUTHENTICATED",
            message="Authentication required",
        )

    agent = db.query(Agent).filter(Agent.id == agent_uuid).first()
    if not agent:
        raise AppException(
            status_code=401,
            code="NOT_AUTHENTICATED",
            message="Authentication required",
        )

    return agent


def check_agent_assigned(current_agent: Agent, target_agent_id: uuid.UUID | str) -> None:
    """
    Enforces that an authenticated agent can only access their own resource/schedule.
    Raises 403 NOT_ASSIGNED if the agent IDs do not match.
    """
    if str(current_agent.id).strip().lower() != str(target_agent_id).strip().lower():
        raise AppException(
            status_code=403,
            code="NOT_ASSIGNED",
            message="You are not assigned to this request",
        )
