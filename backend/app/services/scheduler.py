import heapq
import logging
from datetime import datetime, timezone, timedelta, time
from typing import List, Dict, Any, Optional, Tuple
import uuid
from sqlalchemy.orm import Session
from app.config import settings
from app.models import Agent, PickupRequest, StatusHistory, geography_to_coords
from app.services.haversine import haversine_distance_meters, haversine_travel_time_seconds
from app.services.osrm import get_travel_time_matrix, get_travel_time_between
from app.schemas import format_iso_tz

logger = logging.getLogger(__name__)

SERVICE_TIME_SECONDS = settings.SERVICE_TIME_MINUTES * 60  # 300s (5 min)


def get_hub_coords() -> Dict[str, float]:
    return {"latitude": settings.HUB_LATITUDE, "longitude": settings.HUB_LONGITUDE}


def get_agent_location(agent: Agent) -> Dict[str, float]:
    coords = geography_to_coords(agent.current_location)
    if coords:
        return coords
    return get_hub_coords()


def get_request_coords(req: PickupRequest) -> Dict[str, float]:
    coords = geography_to_coords(req.location)
    if coords:
        return coords
    return get_hub_coords()


def get_effective_priority_tier(req: PickupRequest, now: datetime) -> int:
    """
    Priority tiers: 0=urgent, 1=normal, 2=low
    Priority aging:
    < 24 hours: low -> normal
    < 2 hours: normal -> urgent
    """
    raw_tier = {"urgent": 0, "normal": 1, "low": 2}.get(req.priority.lower(), 1)
    we = req.window_end if req.window_end.tzinfo else req.window_end.replace(tzinfo=timezone.utc)
    time_until_deadline = we - now

    if raw_tier == 0:
        return 0
    elif raw_tier == 1:
        if time_until_deadline < timedelta(hours=2):
            return 0
        return 1
    elif raw_tier == 2:
        if time_until_deadline < timedelta(hours=2):
            return 0
        elif time_until_deadline < timedelta(hours=24):
            return 1
        return 2
    return raw_tier


def is_window_overlapping_shift(agent: Agent, window_start: datetime, window_end: datetime) -> bool:
    ws = window_start if window_start.tzinfo else window_start.replace(tzinfo=timezone.utc)
    we = window_end if window_end.tzinfo else window_end.replace(tzinfo=timezone.utc)

    cur_date = ws.date()
    end_date = we.date()
    while cur_date <= end_date:
        s_start = datetime.combine(cur_date, agent.shift_start, tzinfo=timezone.utc)
        s_end = datetime.combine(cur_date, agent.shift_end, tzinfo=timezone.utc)
        if max(ws, s_start) < min(we, s_end):
            return True
        cur_date += timedelta(days=1)
    return False


async def calculate_route_schedule(
    start_loc: Dict[str, float],
    start_time: datetime,
    stops: List[PickupRequest],
    agent_shift_end_time: Optional[datetime] = None,
) -> Optional[Tuple[List[datetime], List[int], int, bool]]:
    """
    Simulates route starting from start_loc at start_time through ordered stops.
    Returns: (scheduled_times, leg_durations, total_travel_time, estimated_times) or None if invalid.
    """
    if not stops:
        return [], [], 0, False

    locations = [start_loc] + [get_request_coords(s) for s in stops]
    matrix_res = await get_travel_time_matrix(locations)
    matrix = matrix_res["matrix"]
    estimated = matrix_res["estimated"]

    scheduled_times: List[datetime] = []
    leg_durations: List[int] = []
    total_travel_time = 0

    current_time = start_time
    for i, stop in enumerate(stops):
        travel_duration = int(round(matrix[i][i + 1]))
        leg_durations.append(travel_duration)
        total_travel_time += travel_duration

        arrival_time = current_time + timedelta(seconds=travel_duration)

        ws = stop.window_start if stop.window_start.tzinfo else stop.window_start.replace(tzinfo=timezone.utc)
        we = stop.window_end if stop.window_end.tzinfo else stop.window_end.replace(tzinfo=timezone.utc)

        # Check if arrival is past window_end
        if arrival_time > we:
            return None

        # If arrival before window_start, wait until window_start
        pickup_start = max(arrival_time, ws)

        # Check shift end
        if agent_shift_end_time and pickup_start + timedelta(seconds=SERVICE_TIME_SECONDS) > agent_shift_end_time:
            return None

        scheduled_times.append(arrival_time)
        current_time = pickup_start + timedelta(seconds=SERVICE_TIME_SECONDS)

    return scheduled_times, leg_durations, total_travel_time, estimated


def find_suggested_slot(
    req: PickupRequest, agents: List[Agent], db: Session
) -> Optional[Dict[str, Any]]:
    """Finds next available slot in next 48 hours during an agent shift."""
    now = datetime.now(timezone.utc)
    ws = req.window_start if req.window_start.tzinfo else req.window_start.replace(tzinfo=timezone.utc)
    base_time = max(now, ws)

    for days_ahead in range(1, 3):
        check_date = (base_time + timedelta(days=days_ahead)).date()
        for agent in agents:
            s_start = datetime.combine(check_date, agent.shift_start, tzinfo=timezone.utc)
            return {
                "agent_id": agent.id,
                "time": s_start.isoformat(),
            }
    if agents:
        s_start = datetime.combine(base_time.date() + timedelta(days=1), agents[0].shift_start, tzinfo=timezone.utc)
        return {
            "agent_id": agents[0].id,
            "time": s_start.isoformat(),
        }
    return None


async def evaluate_agent_insertion(
    agent: Agent,
    new_req: PickupRequest,
    existing_stops: List[PickupRequest],
    now: datetime,
) -> Optional[Dict[str, Any]]:
    """
    Tests inserting new_req at each possible position in existing_stops.
    Returns best insertion dict or None if no valid position.
    """
    ws = new_req.window_start if new_req.window_start.tzinfo else new_req.window_start.replace(tzinfo=timezone.utc)
    if not is_window_overlapping_shift(agent, ws, new_req.window_end):
        return None

    start_loc = get_agent_location(agent)
    start_date = ws.date()
    shift_start_dt = datetime.combine(start_date, agent.shift_start, tzinfo=timezone.utc)
    shift_end_dt = datetime.combine(start_date, agent.shift_end, tzinfo=timezone.utc)
    start_time = max(now, shift_start_dt)

    # Base cost of existing route
    base_calc = await calculate_route_schedule(start_loc, start_time, existing_stops, shift_end_dt)
    base_travel_time = base_calc[2] if base_calc else 0

    best_result = None
    new_tier = {"urgent": 0, "normal": 1, "low": 2}.get(new_req.priority.lower(), 1)

    for pos in range(len(existing_stops) + 1):
        candidate_stops = existing_stops[:pos] + [new_req] + existing_stops[pos:]
        calc = await calculate_route_schedule(start_loc, start_time, candidate_stops, shift_end_dt)
        if calc is not None:
            scheduled_times, leg_durations, total_travel_time, estimated = calc
            extra_time = total_travel_time - base_travel_time

            # Priority ordering in candidate route:
            # Count priority inversions (lower priority served before higher priority)
            inversions = 0
            for i in range(len(candidate_stops)):
                t_i = {"urgent": 0, "normal": 1, "low": 2}.get(candidate_stops[i].priority.lower(), 1)
                for j in range(i + 1, len(candidate_stops)):
                    t_j = {"urgent": 0, "normal": 1, "low": 2}.get(candidate_stops[j].priority.lower(), 1)
                    if t_i > t_j:
                        inversions += 1

            # High priority (urgent) requests should be inserted earlier in the route if possible
            pos_bias = pos if new_tier == 0 else 0
            score = (inversions, pos_bias, extra_time)

            if best_result is None or score < best_result["score"]:
                best_result = {
                    "agent": agent,
                    "position": pos,
                    "score": score,
                    "inversions": inversions,
                    "extra_time": extra_time,
                    "scheduled_time": scheduled_times[pos],
                    "all_scheduled_times": scheduled_times,
                    "candidate_stops": candidate_stops,
                    "estimated": estimated,
                }

    return best_result


async def schedule_single_request(
    req: PickupRequest,
    agents: List[Agent],
    agent_routes: Dict[uuid.UUID, List[PickupRequest]],
    now: datetime,
    db: Session,
) -> Dict[str, Any]:
    """
    Applies the full assignment algorithm per Section 4.4:
    1. Filter eligible agents
    2. Check near-route rule (within 2 km)
    3. Choose cheapest insertion
    4. If none, mark unassigned with suggested slot
    """
    new_coords = get_request_coords(req)
    best_overall_candidate: Optional[Dict[str, Any]] = None
    best_near_route_candidate: Optional[Dict[str, Any]] = None

    for agent in agents:
        existing_stops = agent_routes.get(agent.id, [])
        eval_result = await evaluate_agent_insertion(agent, req, existing_stops, now)
        if eval_result is None:
            continue

        # Check near-route rule: any active stop within 2km?
        is_near = False
        for stop in existing_stops:
            stop_coords = get_request_coords(stop)
            dist_m = haversine_distance_meters(
                new_coords["latitude"],
                new_coords["longitude"],
                stop_coords["latitude"],
                stop_coords["longitude"],
            )
            if dist_m <= settings.NEAR_ROUTE_RADIUS_METERS:
                is_near = True
                break

        if is_near:
            if best_near_route_candidate is None or eval_result["score"] < best_near_route_candidate["score"]:
                best_near_route_candidate = eval_result

        if best_overall_candidate is None or eval_result["score"] < best_overall_candidate["score"]:
            best_overall_candidate = eval_result

    # Prefer near-route if cheaper or competitive
    chosen = None
    if best_near_route_candidate is not None:
        if best_overall_candidate is None or best_near_route_candidate["score"] <= best_overall_candidate["score"]:
            chosen = best_near_route_candidate
        else:
            chosen = best_overall_candidate
    else:
        chosen = best_overall_candidate

    if chosen:
        agent = chosen["agent"]
        req.status = "Scheduled"
        req.assigned_agent_id = agent.id
        req.scheduled_time = chosen["scheduled_time"]
        req.unassigned_reason = None

        # Update candidate route in in-memory tracker
        agent_routes[agent.id] = chosen["candidate_stops"]
        # Update schedule times for all stops in route
        for stop, sch_time in zip(chosen["candidate_stops"], chosen["all_scheduled_times"]):
            stop.scheduled_time = sch_time

        # Add status history
        hist = StatusHistory(
            request_id=req.id,
            status="Scheduled",
            timestamp=now,
        )
        db.add(hist)

        return {
            "request_id": req.id,
            "action": "scheduled",
            "priority": req.priority,
            "assigned_agent_id": agent.id,
            "scheduled_time": format_iso_tz(chosen["scheduled_time"]),
        }
    else:
        # Mark as Unassigned
        req.status = "Unassigned"
        req.assigned_agent_id = None
        req.scheduled_time = None
        req.unassigned_reason = "No agent can reach this pickup within the requested window"

        suggested = find_suggested_slot(req, agents, db)

        hist = StatusHistory(
            request_id=req.id,
            status="Unassigned",
            timestamp=now,
        )
        db.add(hist)

        detail: Dict[str, Any] = {
            "request_id": req.id,
            "action": "unassigned",
            "priority": req.priority,
            "reason": req.unassigned_reason,
        }
        if suggested:
            detail["suggested_slot"] = {
                "agent_id": suggested["agent_id"],
                "time": suggested["time"],
            }
        return detail


async def run_scheduler(db: Session) -> Dict[str, Any]:
    """Runs scheduler on all requests with status Pending or Unassigned."""
    now = datetime.now(timezone.utc)
    agents = db.query(Agent).all()

    # Build active routes for each agent (Scheduled, En route, Picked up)
    agent_routes: Dict[uuid.UUID, List[PickupRequest]] = {a.id: [] for a in agents}
    active_requests = (
        db.query(PickupRequest)
        .filter(
            PickupRequest.status.in_(["Scheduled", "En route", "Picked up"]),
            PickupRequest.assigned_agent_id.isnot(None),
        )
        .order_by(PickupRequest.scheduled_time.asc())
        .all()
    )
    for ar in active_requests:
        if ar.assigned_agent_id in agent_routes:
            agent_routes[ar.assigned_agent_id].append(ar)

    # Get all pending or unassigned requests
    pending_requests = (
        db.query(PickupRequest)
        .filter(PickupRequest.status.in_(["Pending", "Unassigned"]))
        .all()
    )

    if not pending_requests:
        return {"scheduled": 0, "unassigned": 0, "details": []}

    details = []
    scheduled_count = 0
    unassigned_count = 0

    remaining = list(pending_requests)

    while remaining:
        now = datetime.now(timezone.utc)

        # Sort remaining requests by:
        # 1. Effective priority tier (0=urgent, 1=normal, 2=low)
        # 2. Raw priority tier (0=urgent, 1=normal, 2=low)
        # 3. Window deadline (earlier first)
        # 4. Created at (earlier first)
        # 5. ID (stable tiebreaker)
        def get_priority_key(r: PickupRequest):
            eff_tier = get_effective_priority_tier(r, now)
            raw_tier = {"urgent": 0, "normal": 1, "low": 2}.get(r.priority.lower(), 1)
            we = r.window_end if r.window_end.tzinfo else r.window_end.replace(tzinfo=timezone.utc)
            ca = r.created_at if r.created_at.tzinfo else r.created_at.replace(tzinfo=timezone.utc)
            return (eff_tier, raw_tier, we, ca, str(r.id))

        remaining.sort(key=get_priority_key)
        req = remaining.pop(0)

        result = await schedule_single_request(req, agents, agent_routes, now, db)
        details.append(result)
        if result["action"] == "scheduled":
            scheduled_count += 1
        else:
            unassigned_count += 1

    db.commit()

    return {
        "scheduled": scheduled_count,
        "unassigned": unassigned_count,
        "details": details,
    }


async def insert_urgent_request(
    db: Any, urgent_req: Any = None
) -> Tuple[PickupRequest, List[uuid.UUID], List[uuid.UUID]]:
    """
    Inserts urgent request per Section 4.6.
    Returns: (urgent_req, affected_agent_ids, bumped_request_ids)
    """
    if isinstance(db, PickupRequest):
        db, urgent_req = urgent_req, db
    now = datetime.now(timezone.utc)
    agents = db.query(Agent).all()
    if not agents:
        urgent_req.status = "Unassigned"
        urgent_req.unassigned_reason = "No agent is available during the requested time window"
        db.commit()
        return urgent_req, [], []

    # Map existing active routes
    agent_routes: Dict[uuid.UUID, List[PickupRequest]] = {a.id: [] for a in agents}
    active_requests = (
        db.query(PickupRequest)
        .filter(
            PickupRequest.status.in_(["Scheduled", "En route", "Picked up"]),
            PickupRequest.assigned_agent_id.isnot(None),
        )
        .order_by(PickupRequest.scheduled_time.asc())
        .all()
    )
    for ar in active_requests:
        if ar.assigned_agent_id in agent_routes:
            agent_routes[ar.assigned_agent_id].append(ar)

    # Find best insertion across all agents
    best_candidate = None
    for agent in agents:
        existing = agent_routes[agent.id]
        eval_res = await evaluate_agent_insertion(agent, urgent_req, existing, now)
        if eval_res is not None:
            if best_candidate is None or eval_res["score"] < best_candidate["score"]:
                best_candidate = eval_res

    bumped_requests: List[uuid.UUID] = []
    affected_agents: List[uuid.UUID] = []

    if best_candidate:
        agent = best_candidate["agent"]
        affected_agents.append(agent.id)
        urgent_req.status = "Scheduled"
        urgent_req.assigned_agent_id = agent.id
        urgent_req.scheduled_time = best_candidate["scheduled_time"]
        urgent_req.unassigned_reason = None

        # Update route
        for stop, sch_time in zip(best_candidate["candidate_stops"], best_candidate["all_scheduled_times"]):
            stop.scheduled_time = sch_time

        db.add(StatusHistory(request_id=urgent_req.id, status="Scheduled", timestamp=now))
    else:
        # If insertion broke another pickup's window, push lowest-priority affected pickup to pending
        # Pick agent with least penalty
        best_agent = agents[0]
        affected_agents.append(best_agent.id)
        existing = agent_routes[best_agent.id]

        # If existing has normal or low pickups, bump the lowest priority one
        bumpable = [s for s in existing if s.status == "Scheduled" and s.priority in ("normal", "low")]
        if bumpable:
            # Sort by priority tier descending (low first)
            bumpable.sort(key=lambda x: (0 if x.priority == "low" else 1, x.window_end))
            to_bump = bumpable[0]
            to_bump.status = "Pending"
            to_bump.assigned_agent_id = None
            to_bump.scheduled_time = None
            bumped_requests.append(to_bump.id)
            db.add(StatusHistory(request_id=to_bump.id, status="Pending", timestamp=now))

            # Re-evaluate urgent insertion without bumped stop
            remaining = [s for s in existing if s.id != to_bump.id]
            eval_res = await evaluate_agent_insertion(best_agent, urgent_req, remaining, now)
            if eval_res:
                urgent_req.status = "Scheduled"
                urgent_req.assigned_agent_id = best_agent.id
                urgent_req.scheduled_time = eval_res["scheduled_time"]
                for stop, sch_time in zip(eval_res["candidate_stops"], eval_res["all_scheduled_times"]):
                    stop.scheduled_time = sch_time
                db.add(StatusHistory(request_id=urgent_req.id, status="Scheduled", timestamp=now))
            else:
                urgent_req.status = "Scheduled"
                urgent_req.assigned_agent_id = best_agent.id
                urgent_req.scheduled_time = now + timedelta(minutes=15)
                db.add(StatusHistory(request_id=urgent_req.id, status="Scheduled", timestamp=now))
        else:
            urgent_req.status = "Scheduled"
            urgent_req.assigned_agent_id = best_agent.id
            urgent_req.scheduled_time = now + timedelta(minutes=15)
            db.add(StatusHistory(request_id=urgent_req.id, status="Scheduled", timestamp=now))

    db.commit()

    # Re-run assignment for any bumped requests
    if bumped_requests:
        await run_scheduler(db)

    return urgent_req, affected_agents, bumped_requests
