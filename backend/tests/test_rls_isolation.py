import uuid
from datetime import date
import pytest
import pytest_asyncio
from sqlalchemy import select, text
from app.core.database import get_tenant_db
from app.models.audit import Engagement

@pytest.mark.asyncio
async def test_cross_tenant_isolation_enforced():
    tenant_a_id = uuid.uuid4()
    tenant_b_id = uuid.uuid4()
    slug_suffix = uuid.uuid4().hex[:6]

    # 1. Create Organization records in database
    async with get_tenant_db(org_id=None) as session:
        await session.execute(
            text("""
                INSERT INTO organizations (id, name, slug, kms_key_arn)
                VALUES 
                    (:id_a, 'Alpha Corp', :slug_a, 'arn:aws:kms:us-east-1:111:key/alpha'),
                    (:id_b, 'Beta Corp', :slug_b, 'arn:aws:kms:us-east-1:222:key/beta')
            """),
            {
                "id_a": tenant_a_id, 
                "slug_a": f"alpha-{slug_suffix}",
                "id_b": tenant_b_id, 
                "slug_b": f"beta-{slug_suffix}"
            }
        )

    # 2. As Tenant Alpha: create a SOC 2 engagement
    async with get_tenant_db(org_id=tenant_a_id) as session_a:
        eng_a = Engagement(
            organization_id=tenant_a_id,
            title="Alpha SOC 2 Type II - 2026",
            framework="SOC2_TYPE_II",
            period_start=date(2026, 1, 1),
            period_end=date(2026, 12, 31),
            lead_partner_id=uuid.uuid4(),
        )
        session_a.add(eng_a)

    # 3. As Tenant Beta: query ALL engagements without any WHERE filter
    async with get_tenant_db(org_id=tenant_b_id) as session_b:
        query = select(Engagement)
        result = await session_b.execute(query)
        beta_visible_engagements = result.scalars().all()

        # Database engine must block Alpha's data entirely
        assert len(beta_visible_engagements) == 0, "Security Failure: Tenant Beta was able to view Tenant Alpha data!"

    # 4. As Tenant Alpha: query ALL engagements without any WHERE filter
    async with get_tenant_db(org_id=tenant_a_id) as session_a:
        query = select(Engagement)
        result = await session_a.execute(query)
        alpha_visible_engagements = result.scalars().all()

        # Alpha can see its own engagement
        assert len(alpha_visible_engagements) == 1
        assert alpha_visible_engagements[0].title == "Alpha SOC 2 Type II - 2026"

    print("\n\n>>> [SUCCESS] PostgreSQL Row-Level Security Verified: 0% data leakage across tenants! <<<\n")
