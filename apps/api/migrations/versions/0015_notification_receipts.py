"""Private reminders and explicit guardian reading receipts."""
from alembic import op
revision="0015"
down_revision="0014"
def upgrade():
    op.execute('\nCREATE TABLE notification_dismissals (\n\tuser_id VARCHAR(36) NOT NULL, \n\tkey VARCHAR(200) NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tinstitution_id VARCHAR(36) NOT NULL, \n\tschool_id VARCHAR(36) NOT NULL, \n\tid VARCHAR(36) NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (institution_id, school_id, id), \n\tFOREIGN KEY(institution_id, school_id) REFERENCES schools (institution_id, id), \n\tUNIQUE (institution_id, school_id, user_id, key), \n\tFOREIGN KEY(user_id) REFERENCES users (id)\n)\n\n')
    op.execute('CREATE INDEX ix_notification_dismissals_institution_id ON notification_dismissals (institution_id)')
    op.execute('ALTER TABLE notification_dismissals ENABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE notification_dismissals FORCE ROW LEVEL SECURITY')
    op.execute("CREATE POLICY tenant_isolation ON notification_dismissals USING (institution_id = nullif(current_setting('app.institution_id', true), '')) WITH CHECK (institution_id = nullif(current_setting('app.institution_id', true), ''))")
    op.execute('GRANT SELECT, INSERT ON notification_dismissals TO portal_app')
    op.execute("ALTER TABLE notice_responses ADD COLUMN viewer_role VARCHAR(30) NOT NULL DEFAULT 'legacy'")
    op.execute('ALTER TABLE notice_responses ALTER COLUMN viewer_role DROP DEFAULT')
def downgrade():
    op.drop_column("notice_responses","viewer_role")
    op.drop_table("notification_dismissals")
