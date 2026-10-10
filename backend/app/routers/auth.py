from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import Agent
from app.schemas import LoginRequest, LoginResponse, AgentSummary
from app.auth import verify_password, create_access_token, get_current_agent
from app.utils.validators import AppException

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    # Match agent by username (case-insensitive)
    agent = (
        db.query(Agent)
        .filter(func.lower(Agent.name) == payload.username.strip().lower())
        .first()
    )

    if not agent or not verify_password(payload.password, agent.password_hash):
        raise AppException(
            status_code=401,
            code="INVALID_CREDENTIALS",
            message="Invalid username or password",
        )

    token, expires_in = create_access_token(str(agent.id), agent.name)
    agent_summary = AgentSummary.from_orm_model(agent)

    return LoginResponse(
        access_token=token,
        token_type="bearer",
        expires_in=expires_in,
        agent=agent_summary,
    )


@router.get("/me", response_model=AgentSummary)
def get_me(current_agent: Agent = Depends(get_current_agent)):
    return AgentSummary.from_orm_model(current_agent)
