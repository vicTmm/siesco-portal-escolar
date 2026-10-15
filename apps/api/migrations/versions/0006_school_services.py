"""Communication, private documents and scoped school services."""

from alembic import op

revision = "0006"
down_revision = "0005"


def upgrade():
    op.execute(
        "\nCREATE TABLE notices (\n\ttitle VARCHAR(160) NOT NULL, \n\tbody VARCHAR(6000) NOT NULL, \n\tkind VARCHAR(20) NOT NULL, \n\toptions JSON NOT NULL, \n\tdeadline TIMESTAMP WITH TIME ZONE, \n\tauthor_id VARCHAR(36) NOT NULL, \n\tpublished_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tarchived BOOLEAN NOT NULL, \n\tinstitution_id VARCHAR(36) NOT NULL, \n\tschool_id VARCHAR(36) NOT NULL, \n\tid VARCHAR(36) NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (institution_id, school_id, id), \n\tFOREIGN KEY(institution_id, school_id) REFERENCES schools (institution_id, id), \n\tCHECK (kind IN ('notice','authorization','poll')), \n\tFOREIGN KEY(author_id) REFERENCES users (id)\n)\n\n"
    )
    op.execute("CREATE INDEX ix_notices_institution_id ON notices (institution_id)")
    op.execute("ALTER TABLE notices ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE notices FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON notices USING (institution_id = nullif(current_setting('app.institution_id', true), '')) WITH CHECK (institution_id = nullif(current_setting('app.institution_id', true), ''))"
    )
    op.execute("GRANT SELECT, INSERT, UPDATE ON notices TO portal_app")
    op.execute(
        "\nCREATE TABLE notice_recipients (\n\tnotice_id VARCHAR(36) NOT NULL, \n\tstudent_id VARCHAR(36) NOT NULL, \n\tinstitution_id VARCHAR(36) NOT NULL, \n\tschool_id VARCHAR(36) NOT NULL, \n\tid VARCHAR(36) NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (institution_id, school_id, id), \n\tFOREIGN KEY(institution_id, school_id) REFERENCES schools (institution_id, id), \n\tFOREIGN KEY(institution_id, school_id, notice_id) REFERENCES notices (institution_id, school_id, id), \n\tFOREIGN KEY(institution_id, school_id, student_id) REFERENCES students (institution_id, school_id, id), \n\tUNIQUE (institution_id, school_id, notice_id, student_id)\n)\n\n"
    )
    op.execute(
        "CREATE INDEX ix_notice_recipients_institution_id ON notice_recipients (institution_id)"
    )
    op.execute("ALTER TABLE notice_recipients ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE notice_recipients FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON notice_recipients USING (institution_id = nullif(current_setting('app.institution_id', true), '')) WITH CHECK (institution_id = nullif(current_setting('app.institution_id', true), ''))"
    )
    op.execute("GRANT SELECT, INSERT ON notice_recipients TO portal_app")
    op.execute(
        "\nCREATE TABLE notice_responses (\n\tnotice_id VARCHAR(36) NOT NULL, \n\tstudent_id VARCHAR(36) NOT NULL, \n\tuser_id VARCHAR(36) NOT NULL, \n\tread_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tanswer VARCHAR(200), \n\tanswered_at TIMESTAMP WITH TIME ZONE, \n\tinstitution_id VARCHAR(36) NOT NULL, \n\tschool_id VARCHAR(36) NOT NULL, \n\tid VARCHAR(36) NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (institution_id, school_id, id), \n\tFOREIGN KEY(institution_id, school_id) REFERENCES schools (institution_id, id), \n\tFOREIGN KEY(institution_id, school_id, notice_id) REFERENCES notices (institution_id, school_id, id), \n\tFOREIGN KEY(institution_id, school_id, student_id) REFERENCES students (institution_id, school_id, id), \n\tUNIQUE (institution_id, school_id, notice_id, student_id, user_id), \n\tFOREIGN KEY(user_id) REFERENCES users (id)\n)\n\n"
    )
    op.execute(
        "CREATE INDEX ix_notice_responses_institution_id ON notice_responses (institution_id)"
    )
    op.execute("ALTER TABLE notice_responses ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE notice_responses FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON notice_responses USING (institution_id = nullif(current_setting('app.institution_id', true), '')) WITH CHECK (institution_id = nullif(current_setting('app.institution_id', true), ''))"
    )
    op.execute("GRANT SELECT, INSERT, UPDATE ON notice_responses TO portal_app")
    op.execute(
        "\nCREATE TABLE school_documents (\n\tstudent_id VARCHAR(36) NOT NULL, \n\tkind VARCHAR(30) NOT NULL, \n\ttitle VARCHAR(160) NOT NULL, \n\tcontent BYTEA NOT NULL, \n\tsha256 VARCHAR(64) NOT NULL, \n\ttoken VARCHAR(64) NOT NULL, \n\tissued_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\trevoked BOOLEAN NOT NULL, \n\treason VARCHAR(1000), \n\tinstitution_id VARCHAR(36) NOT NULL, \n\tschool_id VARCHAR(36) NOT NULL, \n\tid VARCHAR(36) NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (institution_id, school_id, id), \n\tFOREIGN KEY(institution_id, school_id) REFERENCES schools (institution_id, id), \n\tUNIQUE (institution_id, id), \n\tFOREIGN KEY(institution_id, school_id, student_id) REFERENCES students (institution_id, school_id, id), \n\tCHECK (kind IN ('enrollment','attendance','report','history'))\n)\n\n"
    )
    op.execute(
        "CREATE INDEX ix_school_documents_institution_id ON school_documents (institution_id)"
    )
    op.execute("ALTER TABLE school_documents ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE school_documents FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON school_documents USING (institution_id = nullif(current_setting('app.institution_id', true), '')) WITH CHECK (institution_id = nullif(current_setting('app.institution_id', true), ''))"
    )
    op.execute("GRANT SELECT, INSERT, UPDATE ON school_documents TO portal_app")
    op.execute(
        "\nCREATE TABLE document_lookups (\n\ttoken_hash VARCHAR(64) NOT NULL, \n\tinstitution_id VARCHAR(36) NOT NULL, \n\tdocument_id VARCHAR(36) NOT NULL, \n\tid VARCHAR(36) NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(institution_id, document_id) REFERENCES school_documents (institution_id, id), \n\tUNIQUE (token_hash), \n\tFOREIGN KEY(institution_id) REFERENCES institutions (id)\n)\n\n"
    )
    op.execute("GRANT SELECT, INSERT ON document_lookups TO portal_app")
    op.execute(
        "\nCREATE TABLE service_records (\n\tmodule VARCHAR(30) NOT NULL, \n\ttitle VARCHAR(160) NOT NULL, \n\tstudent_id VARCHAR(36), \n\tclass_id VARCHAR(36), \n\towner_id VARCHAR(36) NOT NULL, \n\tdata JSON NOT NULL, \n\tstatus VARCHAR(30) NOT NULL, \n\tversion INTEGER NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tinstitution_id VARCHAR(36) NOT NULL, \n\tschool_id VARCHAR(36) NOT NULL, \n\tid VARCHAR(36) NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (institution_id, school_id, id), \n\tFOREIGN KEY(institution_id, school_id) REFERENCES schools (institution_id, id), \n\tFOREIGN KEY(institution_id, school_id, student_id) REFERENCES students (institution_id, school_id, id), \n\tFOREIGN KEY(institution_id, school_id, class_id) REFERENCES classes (institution_id, school_id, id), \n\tCHECK (version>0), \n\tFOREIGN KEY(owner_id) REFERENCES users (id)\n)\n\n"
    )
    op.execute(
        "CREATE INDEX ix_service_records_institution_id ON service_records (institution_id)"
    )
    op.execute("ALTER TABLE service_records ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE service_records FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON service_records USING (institution_id = nullif(current_setting('app.institution_id', true), '')) WITH CHECK (institution_id = nullif(current_setting('app.institution_id', true), ''))"
    )
    op.execute("GRANT SELECT, INSERT, UPDATE ON service_records TO portal_app")
    op.execute(
        "\nCREATE TABLE service_events (\n\trecord_id VARCHAR(36) NOT NULL, \n\taction VARCHAR(30) NOT NULL, \n\tactor_id VARCHAR(36) NOT NULL, \n\tdata JSON NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tinstitution_id VARCHAR(36) NOT NULL, \n\tschool_id VARCHAR(36) NOT NULL, \n\tid VARCHAR(36) NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (institution_id, school_id, id), \n\tFOREIGN KEY(institution_id, school_id) REFERENCES schools (institution_id, id), \n\tFOREIGN KEY(institution_id, school_id, record_id) REFERENCES service_records (institution_id, school_id, id), \n\tFOREIGN KEY(actor_id) REFERENCES users (id)\n)\n\n"
    )
    op.execute(
        "CREATE INDEX ix_service_events_institution_id ON service_events (institution_id)"
    )
    op.execute("ALTER TABLE service_events ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE service_events FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON service_events USING (institution_id = nullif(current_setting('app.institution_id', true), '')) WITH CHECK (institution_id = nullif(current_setting('app.institution_id', true), ''))"
    )
    op.execute("GRANT SELECT, INSERT ON service_events TO portal_app")
    op.execute(
        "\nCREATE TABLE sensitive_grants (\n\tstudent_id VARCHAR(36) NOT NULL, \n\tuser_id VARCHAR(36) NOT NULL, \n\tcategory VARCHAR(20) NOT NULL, \n\tactive BOOLEAN NOT NULL, \n\tinstitution_id VARCHAR(36) NOT NULL, \n\tschool_id VARCHAR(36) NOT NULL, \n\tid VARCHAR(36) NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (institution_id, school_id, id), \n\tFOREIGN KEY(institution_id, school_id) REFERENCES schools (institution_id, id), \n\tFOREIGN KEY(institution_id, school_id, student_id) REFERENCES students (institution_id, school_id, id), \n\tUNIQUE (institution_id, school_id, student_id, user_id, category), \n\tCHECK (category IN ('pei','health')), \n\tFOREIGN KEY(user_id) REFERENCES users (id)\n)\n\n"
    )
    op.execute(
        "CREATE INDEX ix_sensitive_grants_institution_id ON sensitive_grants (institution_id)"
    )
    op.execute("ALTER TABLE sensitive_grants ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE sensitive_grants FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON sensitive_grants USING (institution_id = nullif(current_setting('app.institution_id', true), '')) WITH CHECK (institution_id = nullif(current_setting('app.institution_id', true), ''))"
    )
    op.execute("GRANT SELECT, INSERT, UPDATE ON sensitive_grants TO portal_app")
    op.execute(
        "\nCREATE TABLE meeting_slots (\n\tteacher_id VARCHAR(36) NOT NULL, \n\tstarts_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tends_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tstudent_id VARCHAR(36), \n\tbooked_by VARCHAR(36), \n\tversion INTEGER NOT NULL, \n\tinstitution_id VARCHAR(36) NOT NULL, \n\tschool_id VARCHAR(36) NOT NULL, \n\tid VARCHAR(36) NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (institution_id, school_id, id), \n\tFOREIGN KEY(institution_id, school_id) REFERENCES schools (institution_id, id), \n\tFOREIGN KEY(institution_id, school_id, teacher_id) REFERENCES teachers (institution_id, school_id, id), \n\tFOREIGN KEY(institution_id, school_id, student_id) REFERENCES students (institution_id, school_id, id), \n\tCHECK (ends_at > starts_at), \n\tCHECK (version>0), \n\tFOREIGN KEY(booked_by) REFERENCES users (id)\n)\n\n"
    )
    op.execute(
        "CREATE INDEX ix_meeting_slots_institution_id ON meeting_slots (institution_id)"
    )
    op.execute("ALTER TABLE meeting_slots ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE meeting_slots FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON meeting_slots USING (institution_id = nullif(current_setting('app.institution_id', true), '')) WITH CHECK (institution_id = nullif(current_setting('app.institution_id', true), ''))"
    )
    op.execute("GRANT SELECT, INSERT, UPDATE ON meeting_slots TO portal_app")
    op.execute(
        "\nCREATE TABLE notice_decisions (\n\tnotice_id VARCHAR(36) NOT NULL, \n\tstudent_id VARCHAR(36) NOT NULL, \n\tuser_id VARCHAR(36) NOT NULL, \n\tanswer VARCHAR(200) NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tinstitution_id VARCHAR(36) NOT NULL, \n\tschool_id VARCHAR(36) NOT NULL, \n\tid VARCHAR(36) NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (institution_id, school_id, id), \n\tFOREIGN KEY(institution_id, school_id) REFERENCES schools (institution_id, id), \n\tFOREIGN KEY(institution_id, school_id, notice_id) REFERENCES notices (institution_id, school_id, id), \n\tFOREIGN KEY(institution_id, school_id, student_id) REFERENCES students (institution_id, school_id, id), \n\tFOREIGN KEY(user_id) REFERENCES users (id)\n)\n\n"
    )
    op.execute(
        "CREATE INDEX ix_notice_decisions_institution_id ON notice_decisions (institution_id)"
    )
    op.execute("ALTER TABLE notice_decisions ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE notice_decisions FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON notice_decisions USING (institution_id = nullif(current_setting('app.institution_id', true), '')) WITH CHECK (institution_id = nullif(current_setting('app.institution_id', true), ''))"
    )
    op.execute("GRANT SELECT, INSERT ON notice_decisions TO portal_app")


def downgrade():
    op.drop_table("notice_decisions")
    op.drop_table("meeting_slots")
    op.drop_table("sensitive_grants")
    op.drop_table("service_events")
    op.drop_table("service_records")
    op.drop_table("document_lookups")
    op.drop_table("school_documents")
    op.drop_table("notice_responses")
    op.drop_table("notice_recipients")
    op.drop_table("notices")
