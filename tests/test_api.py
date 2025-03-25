import pytest, httpx, os, pathlib
from app.main import app

@pytest.mark.asyncio
async def test_create_and_list_students():
    transport = httpx.ASGITransport(app=app)
