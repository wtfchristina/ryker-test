import json
import uuid
from typing import List
from fastapi import APIRouter, Body, Depends, Header, HTTPException, Response, status
from sqlalchemy import select
from app.api.schemas import (
    ControlCreate,
    ControlResponse,
    EngagementCreate,
    EngagementResponse,
    IngestEvidenceRequest,
    SamplingRequest,
)
from app.core.database import get_tenant_db
from app.models.audit import Control, Engagement, EvidenceArtifact
from app.services.sampler import AICPASamplingEngine
from app.services.vault import EvidenceVaultService
from app.services.workpaper import WorkpaperGeneratorService

router = APIRouter(prefix="/api/v1", tags=["Ryker Audit API"])

def get_current_org_id(x_tenant_id: str = Header(...)) -> uuid.UUID:
    try:
        return uuid.UUID(x_tenant_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid X-Tenant-ID header format. Must be UUID.",
        )

@router.post("/engagements", response_model=EngagementResponse, status_code=status.HTTP_201_CREATED)
async def create_engagement(
    payload: EngagementCreate = Body(...),
    org_id: uuid.UUID = Depends(get_current_org_id),
):
    async with get_tenant_db(org_id=org_id) as session:
        engagement = Engagement(
            organization_id=org_id,
            title=payload.title,
            framework=payload.framework,
            period_start=payload.period_start,
            period_end=payload.period_end,
            lead_partner_id=payload.lead_partner_id,
        )
        session.add(engagement)
        await session.flush()
        return engagement

@router.get("/engagements", response_model=List[EngagementResponse])
async def list_engagements(
    org_id: uuid.UUID = Depends(get_current_org_id),
):
    async with get_tenant_db(org_id=org_id) as session:
        result = await session.execute(select(Engagement))
        return result.scalars().all()

@router.post("/engagements/{engagement_id}/controls", response_model=ControlResponse, status_code=status.HTTP_201_CREATED)
async def add_control(
    engagement_id: uuid.UUID,
    payload: ControlCreate = Body(...),
    org_id: uuid.UUID = Depends(get_current_org_id),
):
    async with get_tenant_db(org_id=org_id) as session:
        control = Control(
            organization_id=org_id,
            engagement_id=engagement_id,
            framework_code=payload.framework_code,
            name=payload.name,
            description=payload.description,
            testing_procedure=payload.testing_procedure,
            frequency=payload.frequency,
        )
        session.add(control)
        await session.flush()
        return control

@router.post("/engagements/{engagement_id}/evidence/seal", status_code=status.HTTP_201_CREATED)
async def seal_evidence(
    engagement_id: uuid.UUID,
    payload: IngestEvidenceRequest = Body(...),
    org_id: uuid.UUID = Depends(get_current_org_id),
):
    vault = EvidenceVaultService()
    raw_bytes = json.dumps(payload.payload, sort_keys=True).encode("utf-8")

    result = vault.seal_evidence_payload(
        organization_id=org_id,
        engagement_id=engagement_id,
        control_id=payload.control_id,
        control_code=payload.control_code,
        source_name=payload.source_name,
        file_name=payload.file_name,
        raw_bytes=raw_bytes,
        uploaded_by=payload.uploaded_by,
    )

    async with get_tenant_db(org_id=org_id) as session:
        session.add(result["artifact_model"])

    return {
        "status": "SEALED_IN_VAULT",
        "sha256": result["sha256_hash"],
        "s3_key": result["s3_key"],
        "legal_hold": "ACTIVE",
    }

@router.post("/engagements/{engagement_id}/sample")
async def generate_aicpa_sample(
    engagement_id: uuid.UUID,
    payload: SamplingRequest = Body(...),
    org_id: uuid.UUID = Depends(get_current_org_id),
):
    seed = payload.seed_override or f"{engagement_id}-{payload.control_id}"
    sampled_result = AICPASamplingEngine.select_reproducible_sample(
        population=payload.population,
        sample_seed=seed,
    )
    return sampled_result

@router.get("/engagements/{engagement_id}/workpaper")
async def export_audit_workpaper(
    engagement_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org_id),
):
    async with get_tenant_db(org_id=org_id) as session:
        eng_res = await session.execute(
            select(Engagement).where(Engagement.id == engagement_id)
        )
        engagement = eng_res.scalar_one_or_none()
        if not engagement:
            raise HTTPException(status_code=404, detail="Engagement not found")

        ctrl_res = await session.execute(
            select(Control).where(Control.engagement_id == engagement_id)
        )
        controls = ctrl_res.scalars().all()

        art_res = await session.execute(
            select(EvidenceArtifact).where(EvidenceArtifact.organization_id == org_id)
        )
        artifacts = art_res.scalars().all()

        workpaper_md = WorkpaperGeneratorService.generate_markdown_workpaper(
            engagement=engagement,
            controls=controls,
            artifacts=artifacts,
        )
        return Response(content=workpaper_md, media_type="text/markdown")
