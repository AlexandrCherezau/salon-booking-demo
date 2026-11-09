from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import create_app

TOMORROW = (date.today() + timedelta(days=1)).isoformat()


@pytest.fixture()
def client(tmp_path):
    return TestClient(create_app(tmp_path / "test.sqlite3"))


def book(client, **overrides):
    payload = {"service_id": "cut-women", "master_id": "anna", "day": TOMORROW,
               "hour": 12, "name": "Мария", "phone": "+7 (999) 123-45-67"}
    payload.update(overrides)
    return client.post("/api/bookings", json=payload)


def test_slots_full_day_when_empty(client):
    r = client.get("/api/slots", params={"service_id": "cut-women",
                                         "master_id": "anna", "day": TOMORROW})
    assert r.status_code == 200
    assert r.json()["slots"][0] == "10:00" and r.json()["slots"][-1] == "19:00"


def test_booking_created_and_slot_removed(client):
    r = book(client)
    assert r.status_code == 201
    assert r.json()["time"] == "12:00"
    slots = client.get("/api/slots", params={"service_id": "cut-women",
                                             "master_id": "anna", "day": TOMORROW}).json()["slots"]
    assert "12:00" not in slots and "11:00" in slots


def test_taken_slot_rejected(client):
    assert book(client).status_code == 201
    r = book(client, name="Другой клиент")
    assert r.status_code == 409


def test_multi_hour_service_blocks_overlap(client):
    assert book(client, service_id="color", hour=14).status_code == 201  # 14-16
    assert book(client, hour=15).status_code == 409
    slots = client.get("/api/slots", params={"service_id": "color",
                                             "master_id": "anna", "day": TOMORROW}).json()["slots"]
    assert "13:00" not in slots and "16:00" in slots and "18:00" in slots
    assert "19:00" not in slots  # would end after closing


def test_other_master_same_time_ok(client):
    assert book(client).status_code == 201
    assert book(client, master_id="ilya").status_code == 201


@pytest.mark.parametrize("override,status", [
    ({"master_id": "vera"}, 422),          # master does not do haircuts
    ({"service_id": "nope"}, 404),
    ({"phone": "123"}, 422),
    ({"name": "A"}, 422),
    ({"hour": 21}, 422),                    # after closing
    ({"day": (date.today() - timedelta(days=1)).isoformat()}, 422),
    ({"day": (date.today() + timedelta(days=60)).isoformat()}, 422),
])
def test_validation(client, override, status):
    assert book(client, **override).status_code == status


def test_phone_normalized_and_admin_escapes(client):
    book(client, name="<script>x</script>", phone="89991234567")
    html = client.get("/admin").text
    assert "+7 999 123-45-67" in html
    assert "<script>x" not in html and "&lt;script&gt;" in html


def test_index_served(client):
    r = client.get("/")
    assert r.status_code == 200 and "Лён" in r.text
