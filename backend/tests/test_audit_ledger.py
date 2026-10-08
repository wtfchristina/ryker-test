import io
import uuid
import pytest
from datetime import date
from sqlalchemy import text
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.database import async_session_factory
from app.models.audit import Organization, Engagement, Control

@pytest.mark.asyncio
async def test_audit_event_ledger_tracking():
    org_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    engagement_id = uuid.uuid4()
    control_id = uuid.uuid4()

    async with async_session_factory() as session:
        await session.execute(text(f"SET LOCAL app.current_org_id = '{org_id}'"))

        org = Organization(
            id=org_id,
            name="Ledger Audit Corp",
            slug=f"ledger-{uuid.uuid4().hex[:6]}",
            kms_key_arn="arn:aws:kms:mock:ledger",
        )
        session.add(org)

        engagement = Engagement(
            id=engagement_id,
            organization_id=org_id,
            title="Audit Trail SOC 2",
            framework="SOC2_TYPE2",
            period_start=date.today(),
            period_end=date.today(),
            status="ACTIVE",
            lead_partner_id=actor_id,
        )
        session.add(engagement)

        control = Control(
            id=control_id,
            organization_id=org_id,
            engagement_id=engagement_id,
            framework_code="CC6.2",
            name="User Access Audit",
            description="Log all artifact transactions",
            testing_procedure="Check ledger entries",
            frequency="CONTINUOUS",
        )
        session.add(control)
        await session.commit()

    transport = ASGITransport(app=app)
    headers = {"X-Tenant-ID": str(org_id), "X-User-ID": str(actor_id)}

    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        # 1. Ingest an artifact
        files = {"file": ("ledger_evidence.log", io.BytesIO(b"LEDGER METRICS 2026"), "text/plain")}
        ingest_res = await ac.post(f"/vault/controls/{control_id}/artifacts", files=files, headers=headers)
        assert ingest_res.status_code == 200
        artifact_id = ingest_res.json()["artifact_id"]

        # 2. Verify artifact
        verify_res = await ac.get(f"/vault/artifacts/{artifact_id}/verify", headers=headers)
        assert verify_res.status_code == 200

        # 3. Download artifact
        dl_res = await ac.get(f"/vault/artifacts/{artifact_id}/download", headers=headers)
        assert dl_res.status_code == 200

        # 4. Check audit events endpoint
        ledger_res = await ac.get("/vault/audit-events", headers=headers)
        assert ledger_res.status_code == 200
        events = ledger_res.json()
        actions = [e["action"] for e in events]

        assert "ARTIFACT_INGESTED" in actions
        assert "ARTIFACT_VERIFIED" in actions
        assert "ARTIFACT_DOWNLOADED" in actions
        assert all(e["actor_id"] == str(actor_id) for e in events)
