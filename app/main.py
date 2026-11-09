"""FastAPI app for the demo salon «Лён»: static landing + booking API + admin."""

import os
import re
from datetime import date, datetime, timedelta
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from .admin import render_admin
from .catalog import (BOOKING_HORIZON_DAYS, CLOSE_HOUR, MASTERS, MASTERS_BY_ID,
                      OPEN_HOUR, SERVICES, SERVICES_BY_ID)
from .db import Database, SlotTaken

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
DEFAULT_DB = BASE_DIR / "data" / "salon.sqlite3"


class BookingIn(BaseModel):
    service_id: str
    master_id: str
    day: date
    hour: int = Field(ge=0, le=23)
    name: str = Field(min_length=2, max_length=60)
    phone: str = Field(max_length=30)
    comment: str = Field(default="", max_length=300)

    @field_validator("name", "comment")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return " ".join(value.split())

    @field_validator("phone")
    @classmethod
    def normalize_phone(cls, value: str) -> str:
        digits = re.sub(r"\D", "", value)
        if len(digits) == 11 and digits[0] in "78":
            digits = digits[1:]
        if len(digits) != 10:
            raise ValueError("Телефон должен содержать 10 цифр после +7")
        return f"+7 {digits[:3]} {digits[3:6]}-{digits[6:8]}-{digits[8:]}"


def _validate_pair(service_id: str, master_id: str):
    service = SERVICES_BY_ID.get(service_id)
    master = MASTERS_BY_ID.get(master_id)
    if service is None or master is None:
        raise HTTPException(404, "Неизвестная услуга или мастер")
    if service_id not in master.services:
        raise HTTPException(422, "Этот мастер не выполняет выбранную услугу")
    return service, master


def _validate_day(day: date, today: date) -> None:
    if not today <= day <= today + timedelta(days=BOOKING_HORIZON_DAYS):
        raise HTTPException(422, f"Запись открыта на {BOOKING_HORIZON_DAYS} дней вперёд")


def free_starts(busy: set[int], hours: int, day: date, now: datetime) -> list[int]:
    """Start hours where `hours` consecutive slots are free and not in the past."""
    result = []
    for start in range(OPEN_HOUR, CLOSE_HOUR - hours + 1):
        if day == now.date() and start <= now.hour:
            continue
        if all(h not in busy for h in range(start, start + hours)):
            result.append(start)
    return result


def create_app(db_path: Path | None = None) -> FastAPI:
    db = Database(db_path or Path(os.environ.get("SALON_DB", DEFAULT_DB)))
    app = FastAPI(title="Студия красоты «Лён» — демо", docs_url="/api/docs",
                  redoc_url=None)

    @app.get("/api/catalog")
    def catalog() -> dict:
        return {
            "services": [s.__dict__ for s in SERVICES],
            "masters": [{**m.__dict__, "services": list(m.services)} for m in MASTERS],
            "open_hour": OPEN_HOUR, "close_hour": CLOSE_HOUR,
            "horizon_days": BOOKING_HORIZON_DAYS,
        }

    @app.get("/api/slots")
    def slots(service_id: str, master_id: str, day: date = Query(...)) -> dict:
        service, _ = _validate_pair(service_id, master_id)
        now = datetime.now()
        _validate_day(day, now.date())
        starts = free_starts(db.busy_hours(master_id, day.isoformat()),
                             service.hours, day, now)
        return {"day": day.isoformat(), "duration_hours": service.hours,
                "slots": [f"{h:02d}:00" for h in starts]}

    @app.post("/api/bookings", status_code=201)
    def create_booking(payload: BookingIn) -> dict:
        service, master = _validate_pair(payload.service_id, payload.master_id)
        now = datetime.now()
        _validate_day(payload.day, now.date())
        allowed = free_starts(set(), service.hours, payload.day, now)
        if payload.hour not in allowed:
            raise HTTPException(422, "Это время вне графика работы салона")
        try:
            booking_id = db.create_booking(
                service_id=service.id, master_id=master.id,
                day=payload.day.isoformat(), start_hour=payload.hour,
                hours=service.hours, client_name=payload.name,
                phone=payload.phone, comment=payload.comment)
        except SlotTaken:
            raise HTTPException(409, "Это время уже занято — выберите другое")
        return {"id": booking_id, "service": service.title, "master": master.name,
                "day": payload.day.isoformat(), "time": f"{payload.hour:02d}:00",
                "price": service.price}

    @app.get("/admin", response_class=HTMLResponse)
    def admin() -> str:
        return render_admin(db.list_bookings())

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    return app


app = create_app()
