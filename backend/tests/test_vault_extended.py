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
from app.workers.collector import EvidenceCollectorWorker

@pytest.mark.asyncio
async def test_artifact_download_and_automated_collector():
    org_id = uuid.uuid4()
    engagement_id = uuid.uuid4()
    control_id = uuid.uuid4()

    async with async_session_factory() as session:
        await session.execute(text(f"SET LOCAL app.current_org_id = '{org_id}'"))

        org = Organization(
            id=org_id,
            name="Extended Vault Corp",
            slug=f"ext-{uuid.uuid4().hex[:6]}",
            kms_key_arn="arn:aws:kms:mock:ext",
        )
        session.add(org)

        engagement = Engagement(
            id=engagement_id,
            organization_id=org_id,
            title="Automated Continuous Compliance",
            framework="SOC2_TYPE2",
            period_start=date.today(),
            period_end=date.today(),
            status="ACTIVE",
            lead_partner_id=uuid.uuid4(),
        )
        session.add(engagement)

        control = Control(
            id=control_id,
            organization_id=org_id,
            engagement_id=engagement_id,
            framework_code="CC7.2",
            name="Continuous Monitoring Telemetry",
            description="Collect automated log telemetry",
            testing_procedure="Verify scheduled ingestion",
            frequency="CONTINUOUS",
        )
        session.add(control)
        await session.commit()

    # 1. Run Automated Collector Worker
    worker = EvidenceCollectorWorker(org_id=org_id)
    ingest_result = await worker.collect_and_ingest(control_id=control_id)
    assert ingest_result["status"] == "success"
    artifact_id = ingest_result["artifact_id"]
    expected_hash = ingest_result["sha256_hash"]

    # 2. Download Artifact via API and assert headers and binary integrity
    transport = ASGITransport(app=app)
    headers = {"X-Tenant-ID": str(org_id)}

    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        download_res = await ac.get(f"/vault/artifacts/{artifact_id}/download", headers=headers)
        assert download_res.status_code == 200
        assert download_res.headers["etag"] == f'"{expected_hash}"'
        assert download_res.headers["x-worm-compliant"] == "true"

        # Check raw payload hash matches expected hash
        downloaded_bytes = download_res.content
        assert hashlib.sha256(downloaded_bytes).hexdigest() == expected_hash

        # Cross-tenant download rejection
        headers_other = {"X-Tenant-ID": str(uuid.uuid4())}
        cross_download = await ac.get(f"/vault/artifacts/{artifact_id}/download", headers=headers_other)
        assert cross_download.status_code == 404
