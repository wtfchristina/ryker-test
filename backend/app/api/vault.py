import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from app.core.database import get_tenant_db
from app.api.routes import get_current_org_id
from app.models.audit import Engagement

router = APIRouter(prefix="/vault", tags=["vault"])

@router.post("/engagements/{engagement_id}/seal")
async def seal_engagement(
    engagement_id: uuid.UUID,
    retention_days: int = 365,
    org_id: uuid.UUID = Depends(get_current_org_id),
):
    async with get_tenant_db(org_id=org_id) as session:
        query = select(Engagement).where(Engagement.id == engagement_id)
        result = await session.execute(query)
        engagement = result.scalar_one_or_none()

        if not engagement:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Engagement not found or access denied by RLS policy"
            )

        if engagement.status == "SEALED":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Engagement is already sealed under WORM compliance"
            )

        engagement.status = "SEALED"
        await session.commit()

        return {
            "status": "success",
            "engagement_id": str(engagement_id),
            "sealed": True,
            "worm_retention_days": retention_days
        }
