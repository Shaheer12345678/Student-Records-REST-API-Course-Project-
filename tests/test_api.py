import pytest, httpx, os, pathlib
from app.main import app

@pytest.mark.asyncio
async def test_create_and_list_students():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/students", json={"name":"Alex","email":"a@u.ca"})
        assert r.status_code == 200
        r = await client.get("/students")
        assert any(s["name"]=="Alex" for s in r.json())
