"""Specific purposes for recorded guardian consent."""

from alembic import op

revision = "0011"
down_revision = "0010"


def upgrade():
    op.execute(
        "ALTER TABLE notices ADD COLUMN purpose VARCHAR(30) NOT NULL DEFAULT 'general'"
    )
    op.execute("ALTER TABLE notices ALTER COLUMN purpose DROP DEFAULT")
    op.create_check_constraint(
        "ck_notice_purpose",
        "notices",
        "purpose IN ('general','image','medication','pickup') AND (kind='authorization' OR purpose='general')",
    )


def downgrade():
    op.drop_constraint("ck_notice_purpose", "notices", type_="check")
    op.drop_column("notices", "purpose")
