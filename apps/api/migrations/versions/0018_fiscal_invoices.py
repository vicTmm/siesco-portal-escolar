"""Private NFS-e profiles, durable DPS identities and authorized XML preservation."""

from alembic import op

revision = "0018"
down_revision = "0017"


def upgrade():
    scope = "institution_id VARCHAR(36) NOT NULL, school_id VARCHAR(36) NOT NULL, id VARCHAR(36) PRIMARY KEY, UNIQUE(institution_id,school_id,id), FOREIGN KEY(institution_id,school_id) REFERENCES schools(institution_id,id)"
    op.execute(
        f"CREATE TABLE fiscal_profiles ({scope}, cnpj VARCHAR(14) NOT NULL, environment VARCHAR(20) NOT NULL CHECK(environment IN ('test','production')), series INTEGER NOT NULL, next_number BIGINT NOT NULL, encrypted BYTEA NOT NULL, version INTEGER NOT NULL, UNIQUE(institution_id,school_id), CHECK(series>=1 AND series<=49999 AND next_number>0 AND next_number<=999999999999999 AND version>0))"
    )
    op.execute(
        f"CREATE TABLE fiscal_invoices ({scope}, student_id VARCHAR(36) NOT NULL, guardian_id VARCHAR(36) NOT NULL, actor_id VARCHAR(36) NOT NULL REFERENCES users(id), key VARCHAR(36) NOT NULL, payload_hash VARCHAR(64) NOT NULL, environment VARCHAR(20) NOT NULL CHECK(environment IN ('test','production')), cnpj VARCHAR(14) NOT NULL, series INTEGER NOT NULL, number BIGINT NOT NULL, dps_id VARCHAR(45) NOT NULL, encrypted BYTEA NOT NULL, signed_xml BYTEA, authorized_xml BYTEA, access_key VARCHAR(50), status VARCHAR(20) NOT NULL CHECK(status IN ('draft','submitting','authorized','rejected','unknown')), message VARCHAR(1000) NOT NULL, version INTEGER NOT NULL CHECK(version>0 AND number>0), created_at TIMESTAMPTZ NOT NULL, UNIQUE(institution_id,school_id,key), UNIQUE(cnpj,environment,series,number), FOREIGN KEY(institution_id,school_id,student_id) REFERENCES students(institution_id,school_id,id), FOREIGN KEY(institution_id,school_id,guardian_id) REFERENCES guardians(institution_id,school_id,id))"
    )
    for table in ("fiscal_profiles", "fiscal_invoices"):
        op.execute(f"CREATE INDEX ix_{table}_institution_id ON {table}(institution_id)")
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY tenant_isolation ON {table} USING(institution_id=current_setting('app.institution_id',true)) WITH CHECK(institution_id=current_setting('app.institution_id',true))"
        )
        op.execute(f"GRANT SELECT,INSERT,UPDATE ON {table} TO portal_app")
    op.execute(
        "CREATE INDEX ix_fiscal_invoice_scope_date ON fiscal_invoices(institution_id,school_id,created_at)"
    )
    op.execute("""CREATE FUNCTION protect_fiscal_invoice() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
        IF (to_jsonb(NEW) - ARRAY['status','message','version','signed_xml','authorized_xml','access_key']) IS DISTINCT FROM (to_jsonb(OLD) - ARRAY['status','message','version','signed_xml','authorized_xml','access_key']) THEN RAISE EXCEPTION 'Fiscal draft identity and payload are immutable'; END IF;
        IF OLD.status='authorized' AND to_jsonb(NEW) IS DISTINCT FROM to_jsonb(OLD) THEN RAISE EXCEPTION 'Authorized fiscal document is immutable'; END IF;
        IF OLD.signed_xml IS NOT NULL AND NEW.signed_xml IS DISTINCT FROM OLD.signed_xml THEN RAISE EXCEPTION 'Signed DPS cannot be replaced'; END IF;
        IF NEW.status='authorized' AND (NEW.authorized_xml IS NULL OR NEW.access_key IS NULL) THEN RAISE EXCEPTION 'Authorization requires official XML and access key'; END IF;
        RETURN NEW; END $$""")
    op.execute(
        "CREATE TRIGGER fiscal_invoice_guard BEFORE UPDATE ON fiscal_invoices FOR EACH ROW EXECUTE FUNCTION protect_fiscal_invoice()"
    )


def downgrade():
    op.execute("DROP TABLE fiscal_invoices")
    op.execute("DROP FUNCTION protect_fiscal_invoice()")
    op.execute("DROP TABLE fiscal_profiles")
