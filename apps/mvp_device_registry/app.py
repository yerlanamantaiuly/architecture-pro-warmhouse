import os
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import JSON, Boolean, DateTime, String, create_engine, text
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@localhost:5432/warmhouse_mvp",
)


class Base(DeclarativeBase):
    pass


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    type: Mapped[str] = mapped_column(String(100), nullable=False)
    room_id: Mapped[str] = mapped_column(String(36), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    serial_number: Mapped[str | None] = mapped_column(String(255), nullable=True)
    protocol: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="inactive", nullable=False)
    is_online: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    configuration: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


engine = create_engine(DATABASE_URL, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

app = FastAPI(title="Device Registry Service", version="1.0.0")


class DeviceBase(BaseModel):
    type: str
    roomId: str = Field(..., min_length=1)
    name: str
    serialNumber: str | None = None
    protocol: str | None = None


class CreateDeviceRequest(DeviceBase):
    pass


class UpdateDeviceRequest(BaseModel):
    name: str | None = None
    status: str | None = None
    isOnline: bool | None = None
    configuration: dict[str, Any] | None = None


class DeviceResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    type: str
    roomId: str
    name: str
    serialNumber: str | None = None
    protocol: str | None = None
    status: str
    isOnline: bool
    configuration: dict[str, Any] = Field(default_factory=dict)


@contextmanager
def get_session() -> Session:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def to_response(device: Device) -> DeviceResponse:
    return DeviceResponse(
        id=device.id,
        type=device.type,
        roomId=device.room_id,
        name=device.name,
        serialNumber=device.serial_number,
        protocol=device.protocol,
        status=device.status,
        isOnline=device.is_online,
        configuration=device.configuration or {},
    )


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health() -> dict[str, str]:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ok"}


@app.get("/devices/health")
def devices_health() -> dict[str, str]:
    return health()


@app.get("/devices", response_model=list[DeviceResponse])
def get_devices() -> list[DeviceResponse]:
    with get_session() as session:
        devices = session.query(Device).order_by(Device.registered_at.asc()).all()
        return [to_response(device) for device in devices]


@app.post("/devices", response_model=DeviceResponse, status_code=201)
def create_device(request: CreateDeviceRequest) -> DeviceResponse:
    with get_session() as session:
        device = Device(
            id=str(uuid.uuid4()),
            type=request.type,
            room_id=request.roomId,
            name=request.name,
            serial_number=request.serialNumber,
            protocol=request.protocol or "http",
            status="registered",
            is_online=False,
            configuration={},
        )
        session.add(device)
        session.commit()
        session.refresh(device)
        return to_response(device)


@app.get("/devices/{device_id}", response_model=DeviceResponse)
def get_device(device_id: str) -> DeviceResponse:
    with get_session() as session:
        device = session.get(Device, device_id)
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")
        return to_response(device)


@app.patch("/devices/{device_id}", response_model=DeviceResponse)
def update_device(device_id: str, request: UpdateDeviceRequest) -> DeviceResponse:
    with get_session() as session:
        device = session.get(Device, device_id)
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")

        if request.name is not None:
            device.name = request.name
        if request.status is not None:
            device.status = request.status
        if request.isOnline is not None:
            device.is_online = request.isOnline
        if request.configuration is not None:
            device.configuration = request.configuration

        session.add(device)
        session.commit()
        session.refresh(device)
        return to_response(device)


@app.post("/devices/{device_id}/activate", status_code=202)
def activate_device(device_id: str) -> dict[str, str]:
    with get_session() as session:
        device = session.get(Device, device_id)
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")

        device.status = "active"
        device.is_online = True
        session.add(device)
        session.commit()
        return {"status": "activation_started"}
