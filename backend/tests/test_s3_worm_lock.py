import io
import uuid
import hashlib
import pytest
from fastapi import UploadFile
from app.core.s3_storage import s3_storage_service

@pytest.mark.asyncio
async def test_s3_object_lock_retention_lifecycle():
    # Use isolated test bucket
    s3_storage_service.bucket = f"worm-vault-{uuid.uuid4().hex[:8]}"
    await s3_storage_service.ensure_bucket_exists()

    tenant_id = str(uuid.uuid4())
    control_id = str(uuid.uuid4())
    payload = b"CRITICAL SECURE WORM EVIDENCE AUDIT DUMP 2026"
    expected_hash = hashlib.sha256(payload).hexdigest()

    upload_file = UploadFile(
        file=io.BytesIO(payload),
        filename="worm_locked_evidence.bin",
    )

    # 1. Ingest with Object Lock
    bucket, s3_key, version_id, sha256_hash, file_size = await s3_storage_service.save_artifact_stream(
        tenant_id=tenant_id,
        control_id=control_id,
        file=upload_file,
        retention_days=180,
    )

    assert bucket == s3_storage_service.bucket
    assert sha256_hash == expected_hash
    assert file_size == len(payload)

    # 2. Verify SHA-256 integrity directly from S3 stream
    is_valid = await s3_storage_service.verify_file_integrity(s3_key, expected_hash)
    assert is_valid is True

    # 3. Assert WORM Object Lock mode is COMPLIANCE
    retention_info = await s3_storage_service.get_object_lock_configuration(s3_key, version_id=version_id)
    assert retention_info.get("Mode") == "COMPLIANCE"
    assert "RetainUntilDate" in retention_info
