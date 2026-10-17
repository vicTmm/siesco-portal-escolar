"""Private attachments."""

from alembic import op

revision = "0007"
down_revision = "0006"


def upgrade():
    op.execute(
        "\nCREATE TABLE private_attachments (\n\trecord_id VARCHAR(36) NOT NULL, \n\tfilename VARCHAR(120) NOT NULL, \n\tmime_type VARCHAR(40) NOT NULL, \n\tcontent BYTEA NOT NULL, \n\tsha256 VARCHAR(64) NOT NULL, \n\tuploader_id VARCHAR(36) NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tinstitution_id VARCHAR(36) NOT NULL, \n\tschool_id VARCHAR(36) NOT NULL, \n\tid VARCHAR(36) NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (institution_id, school_id, id), \n\tFOREIGN KEY(institution_id, school_id) REFERENCES schools (institution_id, id), \n\tFOREIGN KEY(institution_id, school_id, record_id) REFERENCES service_records (institution_id, school_id, id), \n\tFOREIGN KEY(uploader_id) REFERENCES users (id)\n)\n\n"
    )
    op.execute(
        "CREATE INDEX ix_private_attachments_institution_id ON private_attachments (institution_id)"
    )
    op.execute("ALTER TABLE private_attachments ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE private_attachments FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON private_attachments USING (institution_id = nullif(current_setting('app.institution_id', true), '')) WITH CHECK (institution_id = nullif(current_setting('app.institution_id', true), ''))"
    )
    op.execute("GRANT SELECT, INSERT ON private_attachments TO portal_app")


def downgrade():
    op.drop_table("private_attachments")
