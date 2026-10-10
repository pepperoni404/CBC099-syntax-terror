from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Agent
from app.schemas import RunScheduleResponse, ScheduleDetailItem, SuggestedSlot
from app.auth import get_current_agent
from app.services.scheduler import run_scheduler

router = APIRouter(prefix="/schedule", tags=["schedule"])


@router.post("/run", response_model=RunScheduleResponse)
async def run_schedule_engine(
    current_agent: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    result = await run_scheduler(db)
    details = []
    for d in result.get("details", []):
        suggested = None
        if "suggested_slot" in d and d["suggested_slot"]:
            suggested = SuggestedSlot(
                agent_id=d["suggested_slot"]["agent_id"],
                time=d["suggested_slot"]["time"],
            )
        details.append(
            ScheduleDetailItem(
                request_id=d["request_id"],
                action=d["action"],
                assigned_agent_id=d.get("assigned_agent_id"),
                scheduled_time=d.get("scheduled_time"),
                reason=d.get("reason"),
                suggested_slot=suggested,
            )
        )

    return RunScheduleResponse(
        scheduled=result.get("scheduled", 0),
        unassigned=result.get("unassigned", 0),
        details=details,
    )
