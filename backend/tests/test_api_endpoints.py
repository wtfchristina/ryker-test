import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from moto import mock_aws
import boto3
from sqlalchemy import text
from app.core.database import get_tenant_db
from app.main import app

@pytest.mark.asyncio
async def test_full_api_workflow_end_to_end():
    tenant_id = uuid.uuid4()
    lead_partner_id = uuid.uuid4()
    slug_suffix = uuid.uuid4().hex[:6]

    # Seed Organization
    async with get_tenant_db(org_id=None) as session:
        await session.execute(
            text("""
                INSERT INTO organizations (id, name, slug, kms_key_arn)
                VALUES (:id, 'API Test Corp', :slug, 'arn:aws:kms:mock')
            """),
            {"id": tenant_id, "slug": f"api-test-{slug_suffix}"}
        )

    headers = {"X-Tenant-ID": str(tenant_id)}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Health check
        res = await ac.get("/health")
        assert res.status_code == 200
        assert res.json()["status"] == "HEALTHY"

        # 2. Create Engagement
        eng_payload = {
            "title": "SOC 2 Type II End-to-End Test",
            "framework": "SOC2_TYPE_II",
            "period_start": "2026-01-01",
            "period_end": "2026-12-31",
            "lead_partner_id": str(lead_partner_id),
        }
        res = await ac.post("/api/v1/engagements", json=eng_payload, headers=headers)
        assert res.status_code == 201
        eng_data = res.json()
        engagement_id = eng_data["id"]

        # 3. Add Control
        ctrl_payload = {
            "framework_code": "CC8.1",
            "name": "Change Authorization",
            "description": "Ensure branch protection and peer review",
            "testing_procedure": "Sample merged PRs from repository",
            "frequency": "CONTINUOUS",
        }
        res = await ac.post(f"/api/v1/engagements/{engagement_id}/controls", json=ctrl_payload, headers=headers)
        assert res.status_code == 201
        control_id = res.json()["id"]

        # 4. Generate AICPA Sample via API
        prs = [{"pr_id": i, "title": f"PR-{i}"} for i in range(1, 35)]
        sample_payload = {
            "control_id": control_id,
            "population": prs,
        }
        res = await ac.post(f"/api/v1/engagements/{engagement_id}/sample", json=sample_payload, headers=headers)
        assert res.status_code == 200
        sample_data = res.json()
        assert sample_data["sample_size"] == 5  # AICPA tier for 34 items is 5

        # 5. Seal Evidence with S3 Mock
        with mock_aws():
            s3 = boto3.client("s3", region_name="us-east-1")
            s3.create_bucket(Bucket="ryker-evidence-vault", ObjectLockEnabledForBucket=True)

            seal_req = {
                "control_id": control_id,
                "control_code": "CC8.1",
                "source_name": "GITHUB_API",
                "file_name": "branch_protection.json",
                "payload": {"enforce_admins": True, "required_reviews": 1},
                "uploaded_by": str(lead_partner_id),
            }
            res = await ac.post(f"/api/v1/engagements/{engagement_id}/evidence/seal", json=seal_req, headers=headers)
            assert res.status_code == 201
            assert res.json()["status"] == "SEALED_IN_VAULT"
            assert res.json()["legal_hold"] == "ACTIVE"

    print("\n\n>>> [SUCCESS] Full REST API Suite Passed: Ingestion, Controls, Sampling, and Vault Active! <<<\n")
