"""School psychologist is a separate, restricted membership role."""

from alembic import op
from sqlalchemy import text

revision = "0017"
down_revision = "0016"


def upgrade():
    op.drop_constraint("memberships_role_check", "memberships", type_="check")
    op.create_check_constraint(
        "memberships_role_check",
        "memberships",
        "role IN ('director','coordinator','secretary','teacher','student','guardian','psychologist')",
    )


def downgrade():
    if op.get_bind().scalar(
        text("SELECT count(*) FROM memberships WHERE role='psychologist'")
    ):
        raise RuntimeError(
            "Revoke psychologist memberships explicitly before downgrading; no access is deleted automatically."
        )
    op.drop_constraint("memberships_role_check", "memberships", type_="check")
    op.create_check_constraint(
        "memberships_role_check",
        "memberships",
        "role IN ('director','coordinator','secretary','teacher','student','guardian')",
    )
