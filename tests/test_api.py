import asyncio
import httpx
import pytest
from fastapi.testclient import TestClient
from computer_inventory.api import create_app
from computer_inventory.async_client import fetch_manufacturers


@pytest.fixture
def client(tmp_path):
    app = create_app("sqlite:///" + (tmp_path / "api.db").as_posix())
    with TestClient(app) as client:
        yield client


@pytest.fixture
def payload():
    return {"inventory_number": "A-1", "type": "Computer", "manufacturer": "Dell",
            "model": "Latitude", "value": "120.50"}


def test_api_crud_statistics(client, payload):
    response = client.post("/devices", json=payload)
    assert response.status_code == 201
    body = response.json()
    device_id = body["id"]
    assert body["value"] == "120.50"
    assert client.get(f"/devices/{device_id}").status_code == 200
    assert len(client.get("/devices", params={"manufacturer": "Dell"}).json()) == 1
    assert len(client.get("/devices", params={"inventory_number": "A-1"}).json()) == 1
    assert client.get("/statistics").json()["total"] == "120.50"
    assert client.get("/devices/statistics").status_code == 200
    mid = body["manufacturer_id"]
    assert len(client.get(f"/manufacturers/{mid}/devices").json()) == 1
    assert client.patch(f"/devices/{device_id}", json={"value": "200"}).json()["value"] == "200.00"
    assert client.post("/devices", json=payload).status_code == 409
    assert client.delete(f"/devices/{device_id}").status_code == 204
    assert client.get(f"/devices/{device_id}").status_code == 404
    assert client.get("/statistics").json()["count"] == 0
    assert client.get("/health").json() == {"status": "ok"}


@pytest.mark.parametrize("value", ["-1", "NaN", "1.001", "1000000000001"])
def test_api_invalid_value(client, payload, value):
    payload["value"] = value
    assert client.post("/devices", json=payload).status_code == 422


def test_api_missing_and_manufacturers(client, payload):
    assert client.patch("/devices/999", json={"value": "1"}).status_code == 404
    assert client.delete("/devices/999").status_code == 404
    assert client.get("/manufacturers/999/devices").status_code == 404
    assert client.post("/manufacturers", json={"name": "Dell"}).status_code == 201
    assert client.post("/manufacturers", json={"name": "Dell"}).status_code == 409
    assert len(client.get("/manufacturers").json()) == 1
    payload["model"] = "   "
    assert client.post("/devices", json=payload).status_code == 422
    assert client.post("/manufacturers", json={"name": " "}).status_code == 422


def test_async_retry_concurrency():
    attempts = {}
    active = 0
    maximum = 0
    async def handler(request):
        nonlocal active, maximum
        active += 1
        maximum = max(maximum, active)
        await asyncio.sleep(0.001)
        active -= 1
        name = request.url.path.split("/")[-1]
        attempts[name] = attempts.get(name, 0) + 1
        return httpx.Response(503 if attempts[name] == 1 else 200, json={"name": name})
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://provider.example") as client:
            return await fetch_manufacturers(client, ["Dell", "HP", "Lenovo"], concurrency=2)
    result = asyncio.run(run())
    assert len(result) == 3 and maximum <= 2
    assert attempts == {"Dell": 2, "HP": 2, "Lenovo": 2}


def test_async_failure_timeout():
    async def run():
        async def handler(request):
            await asyncio.sleep(0.1)
            return httpx.Response(200, json={})
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://provider.example") as client:
            with pytest.raises(TimeoutError):
                await fetch_manufacturers(client, ["Dell"], retries=0, timeout=0.001)
            with pytest.raises(ValueError):
                await fetch_manufacturers(client, ["Dell"], concurrency=0)
    asyncio.run(run())
