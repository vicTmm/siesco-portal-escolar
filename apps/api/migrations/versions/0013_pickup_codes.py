"""One-use pickup authorization codes."""

from alembic import op

revision = "0013"
down_revision = "0012"


def upgrade():
    op.execute(
        "\nCREATE TABLE pickup_codes (\n\trecord_id VARCHAR(36) NOT NULL, \n\ttoken_hash VARCHAR(64) NOT NULL, \n\texpires_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tconsumed_at TIMESTAMP WITH TIME ZONE, \n\tinstitution_id VARCHAR(36) NOT NULL, \n\tschool_id VARCHAR(36) NOT NULL, \n\tid VARCHAR(36) NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (institution_id, school_id, id), \n\tFOREIGN KEY(institution_id, school_id) REFERENCES schools (institution_id, id), \n\tFOREIGN KEY(institution_id, school_id, record_id) REFERENCES service_records (institution_id, school_id, id), \n\tUNIQUE (token_hash)\n)\n\n"
    )
    op.execute(
        "CREATE INDEX ix_pickup_codes_institution_id ON pickup_codes (institution_id)"
    )
    op.execute("ALTER TABLE pickup_codes ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE pickup_codes FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON pickup_codes USING (institution_id = nullif(current_setting('app.institution_id', true), '')) WITH CHECK (institution_id = nullif(current_setting('app.institution_id', true), ''))"
    )
    op.execute("GRANT SELECT, INSERT, UPDATE ON pickup_codes TO portal_app")


def downgrade():
    op.drop_table("pickup_codes")
