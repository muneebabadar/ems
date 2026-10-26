"""End-to-end UI tests: Playwright drives the built React app served by Express."""

import json
from datetime import timedelta

import pytest
from playwright.sync_api import Page, expect


@pytest.fixture
def logged_in(page: Page, app_url, employee):
    page.goto(f"{app_url}/login")
    page.get_by_label("Email").fill(employee["email"])
    page.get_by_label("Password").fill(employee["password"])
    page.get_by_role("button", name="Sign in").click()
    expect(page.get_by_role("heading", name=f"Hi, {employee['name']}")).to_be_visible()
    return page


def test_unauthenticated_user_redirected_to_login(page: Page, app_url):
    page.goto(app_url)
    expect(page).to_have_url(f"{app_url}/login")
    expect(page.get_by_role("heading", name="Employee Login")).to_be_visible()


def test_wrong_password_shows_error(page: Page, app_url, employee):
    page.goto(f"{app_url}/login")
    page.get_by_label("Email").fill(employee["email"])
    page.get_by_label("Password").fill("wrong-password")
    page.get_by_role("button", name="Sign in").click()

    expect(page.get_by_text("Invalid email or password")).to_be_visible()
    expect(page).to_have_url(f"{app_url}/login")


def test_dashboard_initial_state(logged_in: Page):
    expect(logged_in.get_by_role("button", name="Mark Attendance")).to_be_enabled()
    expect(logged_in.get_by_text("No attendance recorded yet.")).to_be_visible()


def test_mark_attendance_disables_button_and_adds_history(logged_in: Page):
    logged_in.get_by_role("button", name="Mark Attendance").click()

    button = logged_in.get_by_role("button", name="Marked Present")
    expect(button).to_be_disabled()
    expect(logged_in.get_by_text("Checked in at")).to_be_visible()
    expect(logged_in.locator("tbody tr")).to_have_count(1)


def test_marked_state_survives_reload_and_relogin(logged_in: Page, app_url, employee):
    logged_in.get_by_role("button", name="Mark Attendance").click()
    expect(logged_in.get_by_role("button", name="Marked Present")).to_be_disabled()

    logged_in.reload()
    expect(logged_in.get_by_role("button", name="Marked Present")).to_be_disabled()

    logged_in.get_by_role("button", name="Log out").click()
    expect(logged_in).to_have_url(f"{app_url}/login")
    logged_in.get_by_label("Email").fill(employee["email"])
    logged_in.get_by_label("Password").fill(employee["password"])
    logged_in.get_by_role("button", name="Sign in").click()
    expect(logged_in.get_by_role("button", name="Marked Present")).to_be_disabled()


def test_history_shows_past_days(page: Page, app_url, employee, db):
    today = db.execute("SELECT (now() AT TIME ZONE 'UTC')::date").fetchone()[0]
    past = today - timedelta(days=2)
    db.execute(
        "INSERT INTO attendance (employee_id, date, day) SELECT id, %s, %s FROM employees WHERE email = %s",
        [past, past.strftime("%A"), employee["email"]],
    )

    page.goto(f"{app_url}/login")
    page.get_by_label("Email").fill(employee["email"])
    page.get_by_label("Password").fill(employee["password"])
    page.get_by_role("button", name="Sign in").click()

    row = page.locator("tbody tr").first
    expect(row).to_contain_text(past.isoformat())
    expect(row).to_contain_text(past.strftime("%A"))
    expect(page.get_by_role("button", name="Mark Attendance")).to_be_enabled()


def test_button_reenables_when_new_day_starts(page: Page, app_url, employee):
    """The first /today response says 'marked, next day in 0.5s'; after that the real
    server (no row for today) answers, so the midnight timer should re-enable the button."""
    calls = {"n": 0}

    def fake_first_today(route):
        calls["n"] += 1
        if calls["n"] == 1:
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps({"marked": True, "checkInTime": "2026-01-01T09:00:00Z", "msUntilNextDay": 500}),
            )
        else:
            route.continue_()

    page.route("**/api/attendance/today", fake_first_today)
    page.goto(f"{app_url}/login")
    page.get_by_label("Email").fill(employee["email"])
    page.get_by_label("Password").fill(employee["password"])
    page.get_by_role("button", name="Sign in").click()

    expect(page.get_by_role("button", name="Marked Present")).to_be_disabled()
    expect(page.get_by_role("button", name="Mark Attendance")).to_be_enabled(timeout=5000)
