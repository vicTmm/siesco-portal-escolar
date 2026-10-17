"""Unsigned draft documents and audience integrity for notice evidence."""

from alembic import op

revision = "0016"
down_revision = "0015"


def upgrade():
    op.drop_constraint("school_documents_kind_check", "school_documents", type_="check")
    op.create_check_constraint(
        "school_documents_kind_check",
        "school_documents",
        "kind IN ('enrollment','attendance','report','history','contract')",
    )
    for name in ["notice_responses", "notice_decisions"]:
        op.create_foreign_key(
            name + "_audience_fk",
            name,
            "notice_recipients",
            ["institution_id", "school_id", "notice_id", "student_id"],
            ["institution_id", "school_id", "notice_id", "student_id"],
        )


def downgrade():
    for name in ["notice_responses", "notice_decisions"]:
        op.drop_constraint(name + "_audience_fk", name, type_="foreignkey")
    op.drop_constraint("school_documents_kind_check", "school_documents", type_="check")
    op.create_check_constraint(
        "school_documents_kind_check",
        "school_documents",
        "kind IN ('enrollment','attendance','report','history')",
    )
