from datetime import date, datetime, timedelta, timezone

import pytest


def _db_today(db):
    # The server uses APP_TIMEZONE=UTC in tests; ask Postgres so we agree with it exactly.
    return db.execute("SELECT (now() AT TIME ZONE 'UTC')::date").fetchone()[0]


@pytest.mark.parametrize(
    "method, path", [("get", "/attendance"), ("get", "/attendance/today"), ("post", "/attendance")]
)
def test_attendance_routes_require_auth(api, method, path):
    assert getattr(api, method)(path).status_code == 401


def test_today_before_marking(auth_api):
    res = auth_api.get("/attendance/today")
    assert res.status_code == 200
    body = res.json()
    assert body["marked"] is False
    assert body["checkInTime"] is None
    assert 0 < body["msUntilNextDay"] <= 24 * 60 * 60 * 1000


def test_mark_attendance(auth_api, db):
    before = datetime.now(timezone.utc)
    res = auth_api.post("/attendance")

    assert res.status_code == 201
    body = res.json()
    today = _db_today(db)
    assert body["date"] == today.isoformat()
    assert body["day"] == today.strftime("%A")
    check_in = datetime.fromisoformat(body["checkInTime"].replace("Z", "+00:00"))
    assert abs((check_in - before).total_seconds()) < 60


def test_today_after_marking(auth_api):
    marked = auth_api.post("/attendance").json()
    body = auth_api.get("/attendance/today").json()
    assert body["marked"] is True
    assert body["checkInTime"] == marked["checkInTime"]


def test_mark_twice_same_day_returns_409_and_keeps_one_row(auth_api, db):
    assert auth_api.post("/attendance").status_code == 201
    second = auth_api.post("/attendance")

    assert second.status_code == 409
    assert db.execute("SELECT count(*) FROM attendance").fetchone()[0] == 1


def test_employee_id_comes_from_session_not_body(auth_api, db, create_employee):
    other = create_employee(email="other@example.com")
    other_id = db.execute("SELECT id FROM employees WHERE email = %s", [other["email"]]).fetchone()[0]

    auth_api.post("/attendance", json={"employee_id": other_id, "employeeId": other_id})

    rows = db.execute("SELECT employee_id FROM attendance").fetchall()
    assert rows and all(r[0] != other_id for r in rows)


def test_new_day_allows_marking_again(auth_api, db, employee):
    # Simulate having marked yesterday by inserting a past row directly.
    yesterday = _db_today(db) - timedelta(days=1)
    db.execute(
        "INSERT INTO attendance (employee_id, date, day, check_in_time) "
        "SELECT id, %s, %s, now() - interval '1 day' FROM employees WHERE email = %s",
        [yesterday, yesterday.strftime("%A"), employee["email"]],
    )

    assert auth_api.get("/attendance/today").json()["marked"] is False
    assert auth_api.post("/attendance").status_code == 201


def test_history_newest_first_with_day_and_time(auth_api, db, employee):
    today = _db_today(db)
    for offset in (3, 1):
        d = today - timedelta(days=offset)
        db.execute(
            "INSERT INTO attendance (employee_id, date, day) "
            "SELECT id, %s, %s FROM employees WHERE email = %s",
            [d, d.strftime("%A"), employee["email"]],
        )
    auth_api.post("/attendance")

    history = auth_api.get("/attendance").json()

    assert [h["date"] for h in history] == [
        today.isoformat(),
        (today - timedelta(days=1)).isoformat(),
        (today - timedelta(days=3)).isoformat(),
    ]
    for h in history:
        assert h["day"] == date.fromisoformat(h["date"]).strftime("%A")
        assert h["checkInTime"]


def test_history_only_shows_own_records(api, auth_api, create_employee):
    auth_api.post("/attendance")

    other = create_employee(email="someone-else@example.com")
    api.cookies.clear()
    api.post("/auth/login", json={"email": other["email"], "password": other["password"]})

    assert api.get("/attendance").json() == []


def test_history_empty(auth_api):
    assert auth_api.get("/attendance").json() == []
