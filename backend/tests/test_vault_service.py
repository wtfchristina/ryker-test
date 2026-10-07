import json
import uuid
from datetime import date
import pytest
from moto import mock_aws
import boto3
from sqlalchemy import select, text
from app.core.database import get_tenant_db
from app.models.audit import Control, Engagement, EvidenceArtifact, Organization
from app.services.vault import EvidenceVaultService

@pytest.mark.asyncio
async def test_evidence_sealed_and_retrieved_with_worm_lock():
    with mock_aws():
        # 1. Initialize Mock S3 with Object Locking enabled
        s3_client = boto3.client("s3", region_name="us-east-1")
        bucket_name = "ryker-evidence-vault"
        
        s3_client.create_bucket(
            Bucket=bucket_name,
            ObjectLockEnabledForBucket=True,
        )

        vault = EvidenceVaultService(
            endpoint_url=None,
            aws_access_key="mock",
            aws_secret_key="mock",
            bucket_name=bucket_name,
        )
        vault.s3 = s3_client

        tenant_id = uuid.uuid4()
        lead_partner_id = uuid.uuid4()
        slug_suffix = uuid.uuid4().hex[:6]

        # 2. Setup Tenant, Engagement, and Control in DB
        async with get_tenant_db(org_id=None) as session:
            await session.execute(
                text("""
                    INSERT INTO organizations (id, name, slug, kms_key_arn)
                    VALUES (:id, 'Vault Audit Corp', :slug, 'arn:aws:kms:mock:vault')
                """),
                {"id": tenant_id, "slug": f"vault-{slug_suffix}"}
            )

        async with get_tenant_db(org_id=tenant_id) as session:
            eng = Engagement(
                organization_id=tenant_id,
                title="SOC 2 Vault Ingestion Test",
                framework="SOC2_TYPE_II",
                period_start=date(2026, 1, 1),
                period_end=date(2026, 12, 31),
                lead_partner_id=lead_partner_id,
            )
            session.add(eng)
            await session.flush()

            ctrl = Control(
                organization_id=tenant_id,
                engagement_id=eng.id,
                framework_code="CC6.1",
                name="Logical Access & Password Policy",
                description="Enforce complexity, MFA, and inactivity lockouts",
                testing_procedure="Inspect IAM policy configurations via AWS API",
                frequency="CONTINUOUS",
            )
            session.add(ctrl)
            await session.flush()

            # 3. Ingest sample AWS IAM evidence payload
            raw_evidence = json.dumps({
                "account_mfa_enabled": True,
                "minimum_password_length": 14,
                "password_reuse_prevention": 24,
                "max_password_age_days": 90,
            }).encode("utf-8")

            result = vault.seal_evidence_payload(
                organization_id=tenant_id,
                engagement_id=eng.id,
                control_id=ctrl.id,
                control_code="CC6.1",
                source_name="AWS_IAM_API",
                file_name="aws_iam_policy.json",
                raw_bytes=raw_evidence,
                uploaded_by=lead_partner_id,
            )

            session.add(result["artifact_model"])

        # 4. Verify artifact in PostgreSQL under RLS
        async with get_tenant_db(org_id=tenant_id) as session:
            stored_artifact = (
                await session.execute(
                    select(EvidenceArtifact).where(EvidenceArtifact.organization_id == tenant_id)
                )
            ).scalars().first()

            assert stored_artifact is not None
            assert stored_artifact.sha256_hash == result["sha256_hash"]
            assert stored_artifact.verification_status == "PENDING_REVIEW"

        # 5. Verify S3 Object Lock Legal Hold via S3 API
        hold_response = vault.s3.get_object_legal_hold(
            Bucket=vault.bucket,
            Key=result["s3_key"],
        )
        assert hold_response["LegalHold"]["Status"] == "ON"

        print("\n\n>>> [SUCCESS] Vault Service Verified: WORM S3 Legal Hold + SHA-256 seal confirmed! <<<\n")
