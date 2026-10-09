import os
import hashlib
from typing import Tuple
from pathlib import Path
from fastapi import UploadFile

STORAGE_ROOT = Path(os.getenv("VAULT_STORAGE_PATH", "/tmp/vault_storage"))

class StorageService:
    def __init__(self, root_dir: Path = STORAGE_ROOT):
        self.root_dir = root_dir
        self.bucket = "ryker-evidence-vault"
        self.root_dir.mkdir(parents=True, exist_ok=True)

    async def save_artifact_stream(
        self, tenant_id: str, control_id: str, file: UploadFile
    ) -> Tuple[str, str, str, str, int]:
        """
        Streams file chunks to storage, calculates SHA-256 hash inline.
        Returns: (s3_bucket, s3_key, s3_version_id, sha256_hash, file_size_bytes)
        """
        relative_key = f"{tenant_id}/{control_id}/{file.filename}"
        local_destination = self.root_dir / tenant_id / control_id / file.filename
        local_destination.parent.mkdir(parents=True, exist_ok=True)

        hasher = hashlib.sha256()
        bytes_written = 0

        with open(local_destination, "wb") as out_file:
            while chunk := await file.read(1024 * 1024):
                hasher.update(chunk)
                out_file.write(chunk)
                bytes_written += len(chunk)

        sha256_hash = hasher.hexdigest()
        version_id = f"v-{hasher.hexdigest()[:12]}"
        return self.bucket, relative_key, version_id, sha256_hash, bytes_written

    def verify_file_integrity(self, s3_key: str, expected_hash: str) -> bool:
        """Reads file from disk and asserts calculated SHA-256 matches expected metadata."""
        local_file = self.root_dir / s3_key
        if not local_file.exists():
            return False

        hasher = hashlib.sha256()
        with open(local_file, "rb") as f:
            while chunk := f.read(1024 * 1024):
                hasher.update(chunk)

        return hasher.hexdigest() == expected_hash

storage_service = StorageService()
