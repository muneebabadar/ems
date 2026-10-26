import subprocess

from conftest import ROOT


def test_health(api):
    res = api.get("/health")
    assert res.status_code == 200
    assert res.json() == {"ok": True}


def test_login_success_sets_httponly_cookie(api, employee):
    res = api.post("/auth/login", json={"email": employee["email"], "password": employee["password"]})

    assert res.status_code == 200
    body = res.json()
    assert body["email"] == employee["email"]
    assert body["name"] == employee["name"]
    assert "password_hash" not in body
    assert "HttpOnly" in res.headers["set-cookie"]


def test_login_is_case_insensitive_on_email(api, create_employee):
    user = create_employee(email="Mixed.Case@Example.com")
    res = api.post("/auth/login", json={"email": "mixed.case@example.com", "password": user["password"]})
    assert res.status_code == 200


def test_login_wrong_password(api, employee):
    res = api.post("/auth/login", json={"email": employee["email"], "password": "wrong"})
    assert res.status_code == 401
    assert res.json()["error"] == "Invalid email or password"


def test_login_unknown_email(api):
    res = api.post("/auth/login", json={"email": "nobody@example.com", "password": "x"})
    assert res.status_code == 401


def test_login_validation(api):
    res = api.post("/auth/login", json={"email": "not-an-email"})
    assert res.status_code == 400


def test_me_requires_auth(api):
    assert api.get("/auth/me").status_code == 401


def test_me_returns_current_employee(auth_api, employee):
    res = auth_api.get("/auth/me")
    assert res.status_code == 200
    assert res.json()["email"] == employee["email"]


def test_tampered_token_rejected(api):
    api.cookies.set("token", "not.a.real.jwt")
    assert api.get("/auth/me").status_code == 401


def test_logout_clears_session(auth_api):
    assert auth_api.post("/auth/logout").status_code == 204
    assert auth_api.get("/auth/me").status_code == 401


def test_unknown_api_route_returns_json_404(api):
    res = api.get("/does-not-exist")
    assert res.status_code == 404
    assert res.json() == {"error": "Not found"}


def test_create_user_rejects_duplicate_email(server_env, employee):
    result = subprocess.run(
        ["node", "server/scripts/create-user.js", "Dup", employee["email"], "pw"],
        cwd=ROOT, env=server_env, capture_output=True, text=True,
    )
    assert result.returncode == 1
    assert "already exists" in result.stderr
