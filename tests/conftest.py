"""Shared fixtures: a throwaway Postgres in Docker plus the real Node server.

Both the backend (requests) and frontend (Playwright) suites talk to the same
running app, so nothing in the JS code is mocked.
"""

import os
import socket
import subprocess
import time
import uuid
from pathlib import Path

import psycopg
import pytest
import requests

ROOT = Path(__file__).resolve().parent.parent
PG_PASSWORD = "test"
TIMEZONE = "UTC"


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_for(check, timeout=30, what="service"):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if check():
                return
        except Exception:
            pass
        time.sleep(0.3)
    raise RuntimeError(f"Timed out waiting for {what}")


@pytest.fixture(scope="session")
def database_url():
    port = _free_port()
    name = f"attendance-test-{uuid.uuid4().hex[:8]}"
    subprocess.run(
        ["docker", "run", "-d", "--rm", "--name", name, "-p", f"{port}:5432",
         "-e", f"POSTGRES_PASSWORD={PG_PASSWORD}", "postgres:16-alpine"],
        check=True, capture_output=True,
    )
    url = f"postgresql://postgres:{PG_PASSWORD}@127.0.0.1:{port}/postgres"
    try:
        _wait_for(lambda: psycopg.connect(url, connect_timeout=2).close() or True, 60, "Postgres")
        with psycopg.connect(url, autocommit=True) as conn:
            conn.execute((ROOT / "db" / "init.sql").read_text())
        yield url
    finally:
        subprocess.run(["docker", "stop", name], capture_output=True)


@pytest.fixture(scope="session")
def server_env(database_url):
    return {
        **os.environ,
        "DATABASE_URL": database_url,
        "DATABASE_SSL": "false",
        "JWT_SECRET": "test-secret",
        "APP_TIMEZONE": TIMEZONE,
        "NODE_ENV": "test",
    }


@pytest.fixture(scope="session")
def app_url(server_env):
    if not (ROOT / "client" / "dist" / "index.html").exists():
        subprocess.run("npm --prefix client run build", shell=True, cwd=ROOT, check=True)

    port = _free_port()
    proc = subprocess.Popen(
        ["node", "server/src/index.js"],
        cwd=ROOT, env={**server_env, "PORT": str(port)},
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    url = f"http://127.0.0.1:{port}"
    try:
        _wait_for(lambda: requests.get(f"{url}/api/health", timeout=1).ok, 30, "Node server")
        yield url
    finally:
        proc.terminate()
        proc.wait(timeout=10)


@pytest.fixture
def db(database_url):
    with psycopg.connect(database_url, autocommit=True) as conn:
        yield conn


@pytest.fixture(autouse=True)
def _clean_tables(request):
    """Every test starts with empty tables (only if the test uses the database)."""
    if "database_url" not in request.fixturenames and "app_url" not in request.fixturenames:
        yield
        return
    url = request.getfixturevalue("database_url")
    with psycopg.connect(url, autocommit=True) as conn:
        conn.execute("TRUNCATE attendance, employees RESTART IDENTITY CASCADE")
    yield


@pytest.fixture
def create_employee(server_env):
    """Creates accounts through the real `create-user` script."""

    def _create(name="Test User", email=None, password="pass1234"):
        email = email or f"user-{uuid.uuid4().hex[:8]}@example.com"
        result = subprocess.run(
            ["node", "server/scripts/create-user.js", name, email, password],
            cwd=ROOT, env=server_env, capture_output=True, text=True,
        )
        assert result.returncode == 0, result.stderr
        return {"name": name, "email": email, "password": password}

    return _create


@pytest.fixture
def employee(create_employee):
    return create_employee()


@pytest.fixture
def api(app_url):
    """Unauthenticated HTTP session with a base URL."""

    class Api(requests.Session):
        def request(self, method, path, *args, **kwargs):
            return super().request(method, f"{app_url}/api{path}", *args, **kwargs)

    with Api() as session:
        yield session


@pytest.fixture
def auth_api(api, employee):
    """HTTP session already logged in as `employee`."""
    res = api.post("/auth/login", json={"email": employee["email"], "password": employee["password"]})
    assert res.status_code == 200, res.text
    return api
