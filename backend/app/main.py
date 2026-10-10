import logging
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.config import settings
from app.utils.validators import AppException
from app.routers import auth, requests, agents, schedule, demo, route

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Smart Courier Pickup Scheduling System API",
    version="1.0.0",
    description="Backend API for managing courier agents, pickup requests, and real-time scheduling.",
)

# CORS Configuration
origins = [origin.strip() for origin in settings.ALLOWED_ORIGINS.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception Handlers matching integration-guide Section 2.3 & 2.4
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    error_payload = {
        "code": exc.code,
        "message": exc.message,
    }
    if exc.field is not None:
        error_payload["field"] = exc.field
    return JSONResponse(status_code=exc.status_code, content={"error": error_payload})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    first_error = errors[0] if errors else {}
    loc = first_error.get("loc", [])
    field_name = str(loc[-1]) if loc else None
    msg = first_error.get("msg", "Validation error")

    code = "INVALID_INPUT"
    if field_name in ["latitude", "longitude"]:
        code = "INVALID_COORDINATES"
        msg = f"{field_name} must be between -90 and 90" if field_name == "latitude" else f"{field_name} must be between -180 and 180"
    elif field_name == "priority":
        code = "INVALID_PRIORITY"
        msg = "priority must be one of: urgent, normal, low"
    elif field_name in ["window_start", "window_end"]:
        code = "INVALID_WINDOW"

    error_payload = {
        "code": code,
        "message": msg,
    }
    if field_name:
        error_payload["field"] = field_name

    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"error": error_payload})


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)

    code = "INTERNAL_ERROR"
    message = str(exc.detail)

    if exc.status_code == 401:
        code = "NOT_AUTHENTICATED"
        message = "Authentication required"
    elif exc.status_code == 403:
        code = "NOT_ASSIGNED"
        message = "You are not assigned to this request"
    elif exc.status_code == 404:
        code = "REQUEST_NOT_FOUND"
        message = "Resource not found"
    elif exc.status_code == 409:
        code = "INVALID_TRANSITION"

    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": code, "message": message}},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled server exception: %s", exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Internal server error",
            }
        },
    )


# Include Routers
app.include_router(auth.router)
app.include_router(requests.router)
app.include_router(agents.router)
app.include_router(schedule.router)
app.include_router(demo.router)
app.include_router(route.router)



@app.get("/health", tags=["system"])
def health_check():
    return {"status": "ok"}
