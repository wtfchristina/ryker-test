import io
import uuid
import hashlib
import pytest
from datetime import date
from sqlalchemy import text
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.database import async_session_factory
from app.models.audit import Organization, Engagement, Control

@pytest.mark.asyncio
async def test_artifact_lifecycle_retrieval_and_verification():
    org_a = uuid.uuid4()
    org_b = uuid.uuid4()
    engagement_id = uuid.uuid4()
    control_id = uuid.uuid4()

    async with async_session_factory() as session:
        await session.execute(text(f"SET LOCAL app.current_org_id = '{org_a}'"))

        org = Organization(
            id=org_a,
            name="Alpha Corp",
            slug=f"alpha-{uuid.uuid4().hex[:6]}",
            kms_key_arn="arn:aws:kms:mock:alpha",
        )
        session.add(org)

        engagement = Engagement(
            id=engagement_id,
            organization_id=org_a,
            title="SOC 2 Ingestion Lifecycle",
            framework="SOC2_TYPE2",
            period_start=date.today(),
            period_end=date.today(),
            status="ACTIVE",
            lead_partner_id=uuid.uuid4(),
        )
        session.add(engagement)

        control = Control(
            id=control_id,
            organization_id=org_a,
            engagement_id=engagement_id,
            framework_code="CC6.8",
            name="Cryptographic Storage Check",
            description="Verify data persistence",
            testing_procedure="Hash compare",
            frequency="CONTINUOUS",
        )
        session.add(control)
        await session.commit()

    transport = ASGITransport(app=app)
    headers_org_a = {"X-Tenant-ID": str(org_a)}
    headers_org_b = {"X-Tenant-ID": str(org_b)}
    payload = b"CRITICAL COMPLIANCE AUDIT BLOB 2026-OCT"

    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        # 1. Ingest file through storage engine
        files = {"file": ("audit_vault.bin", io.BytesIO(payload), "application/octet-stream")}
        ingest_res = await ac.post(
            f"/vault/controls/{control_id}/artifacts",
            files=files,
            headers=headers_org_a,
        )
        assert ingest_res.status_code == 200
        artifact_id = ingest_res.json()["artifact_id"]

        # 2. List artifacts for control
        list_res = await ac.get(f"/vault/controls/{control_id}/artifacts", headers=headers_org_a)
        assert list_res.status_code == 200
        items = list_res.json()
        assert len(items) == 1
        assert items[0]["sha256_hash"] == hashlib.sha256(payload).hexdigest()

        # 3. Cryptographic integrity verification endpoint
        verify_res = await ac.get(f"/vault/artifacts/{artifact_id}/verify", headers=headers_org_a)
        assert verify_res.status_code == 200
        assert verify_res.json()["status"] == "VERIFIED"

        # 4. Multi-tenant isolation: Tenant B cannot verify Tenant A's artifact
        cross_res = await ac.get(f"/vault/artifacts/{artifact_id}/verify", headers=headers_org_b)
        assert cross_res.status_code == 404
