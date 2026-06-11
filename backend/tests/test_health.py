from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_ok():
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["service"] == "desklite-backend"


def test_root_ok():
    res = client.get("/")
    assert res.status_code == 200
    assert res.json()["name"] == "DeskLite API"
