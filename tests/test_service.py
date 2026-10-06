import json
from pathlib import Path

SPEC_FILE = Path(__file__).resolve().parent.parent / "openapi" / "openapi.json"


def test_health(api):
    response = api.get("/health")

    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/json"
    assert response.json() == {"status": "ok"}


def test_request_id_is_generated(api):
    response = api.get("/health")

    assert len(response.headers["X-Request-ID"]) == 36


def test_request_id_is_echoed(api):
    response = api.get("/health", headers={"X-Request-ID": "lesson-42"})

    assert response.headers["X-Request-ID"] == "lesson-42"


def test_unknown_route_returns_404(api):
    response = api.get("/api/v1/authors")

    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}


def test_method_not_allowed(api):
    response = api.patch("/api/v1/books")

    assert response.status_code == 405
    assert "GET" in response.headers["Allow"]


def test_swagger_ui_is_served(api):
    response = api.get("/docs", headers={"Accept": "text/html"})

    assert response.status_code == 200
    assert "text/html" in response.headers["Content-Type"]
    assert "swagger-ui" in response.text


def test_exported_openapi_spec_is_up_to_date(api):
    """Если тест упал — выполните `make openapi` и закоммитьте openapi/openapi.json."""
    live_spec = api.get("/openapi.json").json()

    assert live_spec == json.loads(SPEC_FILE.read_text(encoding="utf-8"))


def test_openapi_describes_bearer_auth(api):
    spec = api.get("/openapi.json").json()

    assert spec["components"]["securitySchemes"]["HTTPBearer"]["scheme"] == "bearer"
    assert {"get", "post"} <= set(spec["paths"]["/api/v1/books"])
