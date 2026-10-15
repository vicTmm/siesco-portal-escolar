"""Preserve original clinical observations; evolution is append-only."""

from alembic import op

revision = "0019"
down_revision = "0018"


def upgrade():
    op.execute("""CREATE FUNCTION protect_psychology_record() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
      IF OLD.module='psychology' AND (to_jsonb(NEW)-'version') IS DISTINCT FROM (to_jsonb(OLD)-'version') THEN
        RAISE EXCEPTION 'Psychology consultation is immutable; append an evolution';
      END IF;
      IF OLD.module!='psychology' AND NEW.module='psychology' THEN RAISE EXCEPTION 'Cannot convert a generic record into a clinical consultation'; END IF;
      RETURN NEW;
    END $$""")
    op.execute(
        "CREATE TRIGGER psychology_record_guard BEFORE UPDATE ON service_records FOR EACH ROW EXECUTE FUNCTION protect_psychology_record()"
    )


def downgrade():
    op.execute("DROP TRIGGER psychology_record_guard ON service_records")
    op.execute("DROP FUNCTION protect_psychology_record()")
