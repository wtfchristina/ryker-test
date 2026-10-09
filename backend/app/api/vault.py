import uuid
import json
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Header
from fastapi.responses import FileResponse
from sqlalchemy import select

from app.core.database import get_tenant_db
from app.api.routes import get_current_org_id
from app.models.audit import Control, Engagement, EvidenceArtifact, AuditEvent
from app.core.storage import storage_service
from app.core.s3_storage import s3_storage_service

router = APIRouter(prefix="/vault", tags=["Vault"])

@router.post("/controls/{control_id}/artifacts", status_code=status.HTTP_200_OK)
async def ingest_evidence_artifact(
    control_id: uuid.UUID,
    file: UploadFile = File(...),
    collected_via: str = Form("MANUAL_UPLOAD"),
    org_id: uuid.UUID = Depends(get_current_org_id),
    x_user_id: Optional[str] = Header(None),
):
    user_id = uuid.UUID(x_user_id) if x_user_id else uuid.uuid4()

    async with get_tenant_db(org_id) as db:
        control_query = await db.execute(
            select(Control).where(Control.id == control_id, Control.organization_id == org_id)
        )
        control = control_query.scalars().first()
        if not control:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Control {control_id} not found or access denied.",
            )

        engagement_query = await db.execute(
            select(Engagement).where(Engagement.id == control.engagement_id)
        )
        engagement = engagement_query.scalars().first()
        if not engagement:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent engagement not found.",
            )

        if engagement.status == "SEALED":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Engagement {engagement.id} is sealed under WORM compliance. No new evidence may be added.",
            )

        s3_bucket, s3_key, s3_version_id, sha256_hash, file_size_bytes = (
            await s3_storage_service.save_artifact_stream(
                tenant_id=str(org_id), control_id=str(control_id), file=file
            )
        )

        artifact_id = uuid.uuid4()
        artifact = EvidenceArtifact(
            id=artifact_id,
            organization_id=org_id,
            control_id=control_id,
            s3_bucket=s3_bucket,
            s3_key=s3_key,
            s3_version_id=s3_version_id,
            file_name=file.filename,
            file_size_bytes=file_size_bytes,
            sha256_hash=sha256_hash,
            collected_via=collected_via,
            uploaded_by=user_id,
            verification_status="PENDING_REVIEW",
            locked_until=datetime.now(timezone.utc) + timedelta(days=365),
        )
        db.add(artifact)

        # Audit Event Logging
        event = AuditEvent(
            id=uuid.uuid4(),
            organization_id=org_id,
            actor_id=user_id,
            action="ARTIFACT_INGESTED",
            target_type="EvidenceArtifact",
            target_id=artifact_id,
            details=json.dumps({"sha256_hash": sha256_hash, "file_name": file.filename}),
        )
        db.add(event)

    return {
        "status": "success",
        "artifact_id": str(artifact.id),
        "sha256_hash": sha256_hash,
        "file_size_bytes": file_size_bytes,
        "s3_bucket": s3_bucket,
        "s3_key": s3_key,
    }

@router.get("/controls/{control_id}/artifacts")
async def list_control_artifacts(
    control_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org_id),
):
    async with get_tenant_db(org_id) as db:
        control_query = await db.execute(
            select(Control).where(Control.id == control_id, Control.organization_id == org_id)
        )
        if not control_query.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Control {control_id} not found.",
            )

        artifacts_query = await db.execute(
            select(EvidenceArtifact).where(
                EvidenceArtifact.control_id == control_id,
                EvidenceArtifact.organization_id == org_id,
            )
        )
        artifacts = artifacts_query.scalars().all()
        return [
            {
                "id": str(a.id),
                "file_name": a.file_name,
                "sha256_hash": a.sha256_hash,
                "file_size_bytes": a.file_size_bytes,
                "s3_bucket": a.s3_bucket,
                "s3_key": a.s3_key,
                "verification_status": a.verification_status,
                "collected_via": a.collected_via,
            "locked_until": a.locked_until.isoformat() if a.locked_until else None,
            }
            for a in artifacts
        ]

@router.get("/artifacts/{artifact_id}/verify")
async def verify_artifact_integrity(
    artifact_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org_id),
    x_user_id: Optional[str] = Header(None),
):
    user_id = uuid.UUID(x_user_id) if x_user_id else uuid.uuid4()

    async with get_tenant_db(org_id) as db:
        artifact_query = await db.execute(
            select(EvidenceArtifact).where(
                EvidenceArtifact.id == artifact_id,
                EvidenceArtifact.organization_id == org_id,
            )
        )
        artifact = artifact_query.scalars().first()
        if not artifact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Evidence artifact {artifact_id} not found.",
            )

        is_valid = await s3_storage_service.verify_file_integrity(
            s3_key=artifact.s3_key,
            expected_hash=artifact.sha256_hash,
        )

        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_412_PRECONDITION_FAILED,
                detail="Integrity check failed: on-disk content does not match recorded SHA-256 hash.",
            )

        # Audit Event Logging
        event = AuditEvent(
            id=uuid.uuid4(),
            organization_id=org_id,
            actor_id=user_id,
            action="ARTIFACT_VERIFIED",
            target_type="EvidenceArtifact",
            target_id=artifact_id,
            details=json.dumps({"sha256_hash": artifact.sha256_hash, "result": "VERIFIED"}),
        )
        db.add(event)

        return {
            "artifact_id": str(artifact.id),
            "status": "VERIFIED",
            "sha256_hash": artifact.sha256_hash,
            "worm_compliant": True,
        }

@router.get("/artifacts/{artifact_id}/download")
async def download_artifact(
    artifact_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org_id),
    x_user_id: Optional[str] = Header(None),
):
    user_id = uuid.UUID(x_user_id) if x_user_id else uuid.uuid4()

    async with get_tenant_db(org_id) as db:
        artifact_query = await db.execute(
            select(EvidenceArtifact).where(
                EvidenceArtifact.id == artifact_id,
                EvidenceArtifact.organization_id == org_id,
            )
        )
        artifact = artifact_query.scalars().first()
        if not artifact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Evidence artifact {artifact_id} not found.",
            )

        file_path = storage_service.root_dir / artifact.s3_key
        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Underlying artifact file missing from storage volume.",
            )

        if not await s3_storage_service.verify_file_integrity(artifact.s3_key, artifact.sha256_hash):
            raise HTTPException(
                status_code=status.HTTP_412_PRECONDITION_FAILED,
                detail="Artifact failed cryptographic validation before egress.",
            )

        # Audit Event Logging
        event = AuditEvent(
            id=uuid.uuid4(),
            organization_id=org_id,
            actor_id=user_id,
            action="ARTIFACT_DOWNLOADED",
            target_type="EvidenceArtifact",
            target_id=artifact_id,
            details=json.dumps({"file_name": artifact.file_name}),
        )
        db.add(event)

        headers = {
            "ETag": f'"{artifact.sha256_hash}"',
            "X-Content-SHA256": artifact.sha256_hash,
            "X-WORM-Compliant": "true",
        }
        return FileResponse(
            path=file_path,
            filename=artifact.file_name,
            media_type="application/octet-stream",
            headers=headers,
        )

@router.get("/audit-events")
async def list_audit_events(
    org_id: uuid.UUID = Depends(get_current_org_id),
):
    async with get_tenant_db(org_id) as db:
        events_query = await db.execute(
            select(AuditEvent).where(AuditEvent.organization_id == org_id).order_by(AuditEvent.created_at.desc())
        )
        events = events_query.scalars().all()
        return [
            {
                "id": str(e.id),
                "actor_id": str(e.actor_id),
                "action": e.action,
                "target_type": e.target_type,
                "target_id": str(e.target_id),
                "details": e.details,
            }
            for e in events
        ]
