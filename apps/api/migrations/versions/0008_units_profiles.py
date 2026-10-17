"""Multiple school units and explicit membership selection."""

from alembic import op

revision = "0008"
down_revision = "0007"


def upgrade():
    op.drop_constraint("schools_institution_id_key", "schools", type_="unique")
    op.drop_constraint(
        "memberships_user_id_institution_id_key", "memberships", type_="unique"
    )
    op.create_unique_constraint(
        "memberships_user_unit_role_key",
        "memberships",
        ["user_id", "institution_id", "school_id", "role"],
    )


def downgrade():
    op.drop_constraint("memberships_user_unit_role_key", "memberships", type_="unique")
    op.create_unique_constraint(
        "memberships_user_id_institution_id_key",
        "memberships",
        ["user_id", "institution_id"],
    )
    op.create_unique_constraint(
        "schools_institution_id_key", "schools", ["institution_id"]
    )
