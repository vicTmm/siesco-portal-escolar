"""Annual grading and encrypted optional MFA."""
from alembic import op

revision="0004"
down_revision="0003"

def upgrade():
    op.execute('ALTER TABLE users ADD COLUMN mfa_secret VARCHAR(255)')
    op.execute('ALTER TABLE users ADD COLUMN mfa_pending VARCHAR(255)')
    op.execute('ALTER TABLE users ADD COLUMN mfa_step INTEGER NOT NULL DEFAULT 0')
    op.execute("ALTER TABLE users ADD COLUMN mfa_recovery JSON NOT NULL DEFAULT '[]'")
    op.execute('ALTER TABLE users ALTER COLUMN mfa_step DROP DEFAULT')
    op.execute('ALTER TABLE users ALTER COLUMN mfa_recovery DROP DEFAULT')
    op.execute('\nCREATE TABLE annual_policies (\n\tacademic_year_id VARCHAR(36) NOT NULL, \n\tpolicy_id VARCHAR(36) NOT NULL, \n\tname VARCHAR(160) NOT NULL, \n\tweights JSON NOT NULL, \n\tinstitution_id VARCHAR(36) NOT NULL, \n\tschool_id VARCHAR(36) NOT NULL, \n\tid VARCHAR(36) NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (institution_id, school_id, id), \n\tFOREIGN KEY(institution_id, school_id) REFERENCES schools (institution_id, id), \n\tFOREIGN KEY(institution_id, school_id, academic_year_id) REFERENCES academic_years (institution_id, school_id, id), \n\tFOREIGN KEY(institution_id, school_id, policy_id) REFERENCES grading_policies (institution_id, school_id, id), \n\tUNIQUE (institution_id, school_id, academic_year_id)\n)\n\n')
    op.execute('CREATE INDEX ix_annual_policies_institution_id ON annual_policies (institution_id)')
    op.execute("ALTER TABLE annual_policies ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE annual_policies FORCE ROW LEVEL SECURITY")
    op.execute("CREATE POLICY tenant_isolation ON annual_policies USING (institution_id = nullif(current_setting('app.institution_id', true), '')) WITH CHECK (institution_id = nullif(current_setting('app.institution_id', true), ''))")
    op.execute("GRANT SELECT, INSERT ON annual_policies TO portal_app")
    op.execute('\nCREATE TABLE annual_publications (\n\tannual_policy_id VARCHAR(36) NOT NULL, \n\tstudent_id VARCHAR(36) NOT NULL, \n\trevision INTEGER NOT NULL, \n\tsnapshot JSON NOT NULL, \n\tpublished_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tinstitution_id VARCHAR(36) NOT NULL, \n\tschool_id VARCHAR(36) NOT NULL, \n\tid VARCHAR(36) NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (institution_id, school_id, id), \n\tFOREIGN KEY(institution_id, school_id) REFERENCES schools (institution_id, id), \n\tFOREIGN KEY(institution_id, school_id, annual_policy_id) REFERENCES annual_policies (institution_id, school_id, id), \n\tFOREIGN KEY(institution_id, school_id, student_id) REFERENCES students (institution_id, school_id, id), \n\tUNIQUE (institution_id, school_id, annual_policy_id, student_id, revision)\n)\n\n')
    op.execute('CREATE INDEX ix_annual_publications_institution_id ON annual_publications (institution_id)')
    op.execute("ALTER TABLE annual_publications ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE annual_publications FORCE ROW LEVEL SECURITY")
    op.execute("CREATE POLICY tenant_isolation ON annual_publications USING (institution_id = nullif(current_setting('app.institution_id', true), '')) WITH CHECK (institution_id = nullif(current_setting('app.institution_id', true), ''))")
    op.execute("GRANT SELECT, INSERT ON annual_publications TO portal_app")

def downgrade():
    op.drop_table("annual_publications")
    op.drop_table("annual_policies")
    op.drop_column("users","mfa_recovery")
    op.drop_column("users","mfa_step")
    op.drop_column("users","mfa_pending")
    op.drop_column("users","mfa_secret")
