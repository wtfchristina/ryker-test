"""init_schema_and_tenant_rls

Revision ID: 3e25b7cd62a4
Revises: 
Create Date: 2026-10-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from app.models.audit import Base

# revision identifiers, used by Alembic.
revision: str = '3e25b7cd62a4'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create table schema
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)

    # 2. Enforce Row-Level Security on engagements
    op.execute("ALTER TABLE engagements ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE engagements FORCE ROW LEVEL SECURITY;")
    op.execute("DROP POLICY IF EXISTS tenant_isolation_policy ON engagements;")
    op.execute("""
        CREATE POLICY tenant_isolation_policy ON engagements
            FOR ALL
            TO ryker_app_user
            USING (organization_id::text = current_setting('app.current_org_id', true))
            WITH CHECK (organization_id::text = current_setting('app.current_org_id', true));
    """)


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation_policy ON engagements;")
    op.execute("ALTER TABLE engagements DISABLE ROW LEVEL SECURITY;")
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
