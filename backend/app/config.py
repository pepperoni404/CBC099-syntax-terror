import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://courier:courier@db:5432/courier")
    JWT_SECRET: str = os.getenv("JWT_SECRET", "hackathon-secret-key-change-in-production")
    JWT_EXPIRY_HOURS: int = int(os.getenv("JWT_EXPIRY_HOURS", "8"))
    OSRM_URL: str = os.getenv("OSRM_URL", "https://router.project-osrm.org")
    OSRM_TIMEOUT: float = float(os.getenv("OSRM_TIMEOUT", "3.0"))
    HUB_LATITUDE: float = float(os.getenv("HUB_LATITUDE", "12.9716"))
    HUB_LONGITUDE: float = float(os.getenv("HUB_LONGITUDE", "77.5946"))
    SERVICE_TIME_MINUTES: int = int(os.getenv("SERVICE_TIME_MINUTES", "5"))
    NEAR_ROUTE_RADIUS_METERS: float = float(os.getenv("NEAR_ROUTE_RADIUS_METERS", "2000"))
    FALLBACK_ROAD_FACTOR: float = float(os.getenv("FALLBACK_ROAD_FACTOR", "1.3"))
    FALLBACK_SPEED_KMH: float = float(os.getenv("FALLBACK_SPEED_KMH", "30"))
    ALLOWED_ORIGINS: str = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")

    model_config = SettingsConfigDict(env_file=".env", extra="allow")


settings = Settings()

HUB_LOCATION = {
    "latitude": settings.HUB_LATITUDE,
    "longitude": settings.HUB_LONGITUDE,
}
