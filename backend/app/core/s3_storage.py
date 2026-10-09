import os
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Tuple, Optional
from fastapi import UploadFile
import aioboto3

class S3StorageService:
    def __init__(self):
        self.endpoint_url = os.getenv("S3_ENDPOINT_URL", "http://127.0.0.1:4566")
        self.aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID", "testing")
        self.aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY", "testing")
        self.region_name = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
        self.bucket = os.getenv("VAULT_S3_BUCKET", "ryker-evidence-vault")
        self.session = aioboto3.Session()

    def _get_client(self):
        return self.session.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
            region_name=self.region_name,
        )

    async def ensure_bucket_exists(self):
        """Ensures bucket exists with Object Lock enabled for WORM compliance."""
        await self.ensure_bucket_exists()
        async with self._get_client() as s3:
            try:
                await s3.head_bucket(Bucket=self.bucket)
            except Exception:
                await s3.create_bucket(
                    Bucket=self.bucket,
                    ObjectLockEnabledForBucket=True,
                )

    async def save_artifact_stream(
        self, tenant_id: str, control_id: str, file: UploadFile, retention_days: int = 365
    ) -> Tuple[str, str, str, str, int]:
        """
        Streams file to S3 with inline SHA-256 calculation and applies WORM Object Lock.
        Returns: (s3_bucket, s3_key, s3_version_id, sha256_hash, file_size_bytes)
        """
        s3_key = f"{tenant_id}/{control_id}/{file.filename}"
        hasher = hashlib.sha256()
        buffer = bytearray()

        while chunk := await file.read(1024 * 1024):
            hasher.update(chunk)
            buffer.extend(chunk)

        sha256_hash = hasher.hexdigest()
        file_size = len(buffer)
        retain_until = datetime.now(timezone.utc) + timedelta(days=retention_days)

        async with self._get_client() as s3:
            # Inline Object Lock during put_object (standard AWS WORM ingestion pattern)
            put_res = await s3.put_object(
                Bucket=self.bucket,
                Key=s3_key,
                Body=bytes(buffer),
                Metadata={"sha256": sha256_hash},
                ObjectLockMode="COMPLIANCE",
                ObjectLockRetainUntilDate=retain_until,
            )
            version_id = put_res.get("VersionId", "null")

        return self.bucket, s3_key, version_id, sha256_hash, file_size

    async def verify_file_integrity(self, s3_key: str, expected_hash: str) -> bool:
        """Streams artifact from S3 and asserts calculated SHA-256 matches expected metadata."""
        async with self._get_client() as s3:
            try:
                obj = await s3.get_object(Bucket=self.bucket, Key=s3_key)
            except Exception:
                return False

            hasher = hashlib.sha256()
            body = obj["Body"]
            while True:
                chunk = await body.read(1024 * 1024)
                if not chunk:
                    break
                hasher.update(chunk)

            return hasher.hexdigest() == expected_hash

    async def get_object_lock_configuration(self, s3_key: str, version_id: Optional[str] = None) -> dict:
        """Retrieves active WORM retention details for the artifact."""
        async with self._get_client() as s3:
            # HeadObject returns ObjectLockMode and ObjectLockRetainUntilDate directly
            kwargs = {"Bucket": self.bucket, "Key": s3_key}
            if version_id and version_id != "null":
                kwargs["VersionId"] = version_id
            res = await s3.head_object(**kwargs)
            return {
                "Mode": res.get("ObjectLockMode"),
                "RetainUntilDate": res.get("ObjectLockRetainUntilDate"),
            }

s3_storage_service = S3StorageService()
