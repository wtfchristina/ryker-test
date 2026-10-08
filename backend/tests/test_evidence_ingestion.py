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
async def test_evidence_ingestion_success_and_worm_rejection():
    org_id = uuid.uuid4()
    engagement_id = uuid.uuid4()
    sealed_engagement_id = uuid.uuid4()
    active_control_id = uuid.uuid4()
    sealed_control_id = uuid.uuid4()
    partner_id = uuid.uuid4()

    async with async_session_factory() as session:
        await session.execute(text(f"SET LOCAL app.current_org_id = '{org_id}'"))

        org = Organization(
            id=org_id,
            name="Evidence Ingestion Corp",
            slug=f"evidence-test-{uuid.uuid4().hex[:6]}",
            kms_key_arn="arn:aws:kms:mock:evidence",
        )
        session.add(org)

        active_engagement = Engagement(
            id=engagement_id,
            organization_id=org_id,
            title="SOC 2 Type II FY26",
            framework="SOC2_TYPE2",
            period_start=date.today(),
            period_end=date.today(),
            status="ACTIVE",
            lead_partner_id=partner_id,
        )
        sealed_engagement = Engagement(
            id=sealed_engagement_id,
            organization_id=org_id,
            title="ISO 27001 FY26",
            framework="ISO27001",
            period_start=date.today(),
            period_end=date.today(),
            status="SEALED",
            lead_partner_id=partner_id,
        )
        session.add_all([active_engagement, sealed_engagement])

        active_control = Control(
            id=active_control_id,
            organization_id=org_id,
            engagement_id=engagement_id,
            framework_code="CC6.1",
            name="Logical Access Control",
            description="Controls governing logical access",
            testing_procedure="Inspect access control lists",
            frequency="CONTINUOUS",
        )
        sealed_control = Control(
            id=sealed_control_id,
            organization_id=org_id,
            engagement_id=sealed_engagement_id,
            framework_code="A.9.1",
            name="Access Control Policy",
            description="ISO access control policy",
            testing_procedure="Review policy sign-offs",
            frequency="ANNUAL",
        )
        session.add_all([active_control, sealed_control])
        await session.commit()

    sample_content = b"SECURE AUDIT TELEMETRY LOG 2026-Q4: ACCESS GRANTED"
    expected_hash = hashlib.sha256(sample_content).hexdigest()

    transport = ASGITransport(app=app)
    headers = {"X-Tenant-ID": str(org_id)}

    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        # 1. Ingestion on ACTIVE control succeeds
        files = {"file": ("audit_log.txt", io.BytesIO(sample_content), "text/plain")}
        data = {"collected_via": "AUTOMATED_COLLECTOR"}

        response = await ac.post(
            f"/vault/controls/{active_control_id}/artifacts",
            files=files,
            data=data,
            headers=headers,
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "success"
        assert payload["sha256_hash"] == expected_hash
        assert payload["file_size_bytes"] == len(sample_content)

        # 2. Ingestion on SEALED control fails with 409 Conflict
        files_sealed = {"file": ("tampered_evidence.txt", io.BytesIO(b"MALICIOUS APPEND"), "text/plain")}
        response_sealed = await ac.post(
            f"/vault/controls/{sealed_control_id}/artifacts",
            files=files_sealed,
            headers=headers,
        )
        assert response_sealed.status_code == 409
        assert "sealed under WORM compliance" in response_sealed.json()["detail"]

        # 3. Non-existent control returns 404
        random_control_id = uuid.uuid4()
        response_missing = await ac.post(
            f"/vault/controls/{random_control_id}/artifacts",
            files={"file": ("log.txt", io.BytesIO(b"data"), "text/plain")},
            headers=headers,
        )
        assert response_missing.status_code == 404
