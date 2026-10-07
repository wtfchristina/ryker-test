import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_seal_engagement_nonexistent():
    random_uuid = str(uuid.uuid4())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            f"/vault/engagements/{random_uuid}/seal",
            headers={"x-tenant-id": str(uuid.uuid4())}
        )
        assert response.status_code == 404
