from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Agent
from app.schemas import SeedDemoResponse, UrgentDemoResponse, UrgentRequestSummary
from app.auth import get_current_agent
from app.services.demo import seed_demo_data, create_urgent_demo_request

router = APIRouter(prefix="/demo", tags=["demo"])


@router.post("/seed", response_model=SeedDemoResponse)
def seed_demo(
    reset: bool = Query(False),
    current_agent: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    agents_cnt, reqs_cnt = seed_demo_data(db, reset=reset)
    return SeedDemoResponse(agents_created=agents_cnt, requests_created=reqs_cnt)


@router.post("/urgent", response_model=UrgentDemoResponse)
async def seed_urgent_demo(
    current_agent: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    res = await create_urgent_demo_request(db)
    req_data = res["request"]
    return UrgentDemoResponse(
        request=UrgentRequestSummary(
            id=req_data["id"],
            customer_name=req_data["customer_name"],
            status=req_data["status"],
            priority=req_data["priority"],
        ),
        affected_agents=res["affected_agents"],
        bumped_requests=res.get("bumped_requests", []),
    )
