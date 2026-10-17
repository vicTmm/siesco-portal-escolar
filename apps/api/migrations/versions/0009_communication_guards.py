"""Protect issued content and add workflow lookup indexes."""

from alembic import op

revision = "0009"
down_revision = "0008"


def upgrade():
    op.execute("""CREATE FUNCTION protect_issued_content() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_TABLE_NAME='notices' THEN
        IF (to_jsonb(NEW)-'archived') IS DISTINCT FROM (to_jsonb(OLD)-'archived') OR (OLD.archived AND NOT NEW.archived) THEN
          RAISE EXCEPTION 'Published notice is immutable' USING ERRCODE='23514';
        END IF;
      ELSE
        IF (to_jsonb(NEW)-ARRAY['revoked','reason']) IS DISTINCT FROM (to_jsonb(OLD)-ARRAY['revoked','reason']) OR (OLD.revoked AND NOT NEW.revoked) THEN
          RAISE EXCEPTION 'Issued document is immutable' USING ERRCODE='23514';
        END IF;
      END IF;
      RETURN NEW;
    END $$""")
    for name in ["notices", "school_documents"]:
        op.execute(
            f"CREATE TRIGGER issued_content_guard BEFORE UPDATE ON {name} FOR EACH ROW EXECUTE FUNCTION protect_issued_content()"
        )
    for name, table, columns in INDEXES:
        op.create_index(name, table, columns)


INDEXES = [
    (
        "ix_notices_scope_date",
        "notices",
        ["institution_id", "school_id", "published_at"],
    ),
    (
        "ix_documents_scope_student",
        "school_documents",
        ["institution_id", "school_id", "student_id", "issued_at"],
    ),
    (
        "ix_services_scope_module",
        "service_records",
        ["institution_id", "school_id", "module", "created_at"],
    ),
    (
        "ix_events_scope_record",
        "service_events",
        ["institution_id", "school_id", "record_id", "created_at"],
    ),
    (
        "ix_attachments_scope_record",
        "private_attachments",
        ["institution_id", "school_id", "record_id"],
    ),
    (
        "ix_meetings_scope_teacher",
        "meeting_slots",
        ["institution_id", "school_id", "teacher_id", "starts_at"],
    ),
]


def downgrade():
    for name, table, columns in reversed(INDEXES):
        op.drop_index(name, table_name=table)
    for name in ["notices", "school_documents"]:
        op.execute(f"DROP TRIGGER issued_content_guard ON {name}")
    op.execute("DROP FUNCTION protect_issued_content()")
