import os
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone

import requests
from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict
from sqlalchemy import DateTime, Float, String, create_engine, text
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@localhost:5432/warmhouse_mvp",
)
TEMPERATURE_API_URL = os.getenv("TEMPERATURE_API_URL", "http://localhost:8081")


class Base(DeclarativeBase):
    pass


class TelemetryReading(Base):
    __tablename__ = "telemetry_readings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    device_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False)
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


engine = create_engine(DATABASE_URL, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

app = FastAPI(title="Telemetry Service", version="1.0.0")


class TelemetryIngestRequest(BaseModel):
    deviceId: str
    metricName: str
    metricValue: float
    unit: str | None = None
    source: str | None = None


class TelemetryReadingResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    deviceId: str
    metricName: str
    metricValue: float
    unit: str | None = None
    source: str | None = None
    recordedAt: datetime


@contextmanager
def get_session() -> Session:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def sensor_id_for_device(device_id: str) -> str:
    return str((uuid.UUID(device_id).int % 3) + 1)


def to_response(reading: TelemetryReading) -> TelemetryReadingResponse:
    return TelemetryReadingResponse(
        deviceId=reading.device_id,
        metricName=reading.metric_name,
        metricValue=reading.metric_value,
        unit=reading.unit,
        source=reading.source,
        recordedAt=reading.recorded_at,
    )


def store_reading(
    session: Session,
    device_id: str,
    metric_name: str,
    metric_value: float,
    unit: str | None,
    source: str | None,
) -> TelemetryReading:
    reading = TelemetryReading(
        id=str(uuid.uuid4()),
        device_id=device_id,
        metric_name=metric_name,
        metric_value=metric_value,
        unit=unit,
        source=source or "unknown",
        recorded_at=datetime.now(timezone.utc),
    )
    session.add(reading)
    session.commit()
    session.refresh(reading)
    return reading


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health() -> dict[str, str]:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ok"}


@app.get("/telemetry/health")
def telemetry_health() -> dict[str, str]:
    return health()


@app.get("/telemetry/devices/{device_id}/latest", response_model=TelemetryReadingResponse)
def get_latest_telemetry(device_id: str) -> TelemetryReadingResponse:
    sensor_id = sensor_id_for_device(device_id)
    response = requests.get(f"{TEMPERATURE_API_URL}/temperature/{sensor_id}", timeout=5)
    response.raise_for_status()
    payload = response.json()

    with get_session() as session:
        reading = store_reading(
            session=session,
            device_id=device_id,
            metric_name="temperature",
            metric_value=float(payload["value"]),
            unit=payload.get("unit", "C"),
            source=payload.get("source", "temperature-api"),
        )
        return to_response(reading)


@app.get("/telemetry/devices/{device_id}/history", response_model=list[TelemetryReadingResponse])
def get_history(
    device_id: str,
    metric: str | None = None,
) -> list[TelemetryReadingResponse]:
    with get_session() as session:
        query = session.query(TelemetryReading).filter(TelemetryReading.device_id == device_id)
        if metric:
            query = query.filter(TelemetryReading.metric_name == metric)
        readings = query.order_by(TelemetryReading.recorded_at.desc()).all()
        return [to_response(reading) for reading in readings]


@app.post("/telemetry/ingest", status_code=202)
def ingest(request: TelemetryIngestRequest) -> dict[str, str]:
    with get_session() as session:
        store_reading(
            session=session,
            device_id=request.deviceId,
            metric_name=request.metricName,
            metric_value=request.metricValue,
            unit=request.unit,
            source=request.source or "ingest",
        )
    return {"status": "accepted"}
