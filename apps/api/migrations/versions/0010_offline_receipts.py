"""Idempotent diary synchronization receipts."""

from alembic import op

revision = "0010"
down_revision = "0009"


def upgrade():
    op.execute(
        "\nCREATE TABLE offline_receipts (\n\tjournal_id VARCHAR(36) NOT NULL, \n\tuser_id VARCHAR(36) NOT NULL, \n\tkey VARCHAR(36) NOT NULL, \n\tpayload_hash VARCHAR(64) NOT NULL, \n\tversion INTEGER NOT NULL, \n\tinstitution_id VARCHAR(36) NOT NULL, \n\tschool_id VARCHAR(36) NOT NULL, \n\tid VARCHAR(36) NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (institution_id, school_id, id), \n\tFOREIGN KEY(institution_id, school_id) REFERENCES schools (institution_id, id), \n\tFOREIGN KEY(institution_id, school_id, journal_id) REFERENCES journals (institution_id, school_id, id), \n\tUNIQUE (institution_id, school_id, user_id, key), \n\tCHECK (version>0), \n\tFOREIGN KEY(user_id) REFERENCES users (id)\n)\n\n"
    )
    op.execute(
        "CREATE INDEX ix_offline_receipts_institution_id ON offline_receipts (institution_id)"
    )
    op.execute("ALTER TABLE offline_receipts ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE offline_receipts FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON offline_receipts USING (institution_id = nullif(current_setting('app.institution_id', true), '')) WITH CHECK (institution_id = nullif(current_setting('app.institution_id', true), ''))"
    )
    op.execute("GRANT SELECT, INSERT ON offline_receipts TO portal_app")


def downgrade():
    op.drop_table("offline_receipts")
