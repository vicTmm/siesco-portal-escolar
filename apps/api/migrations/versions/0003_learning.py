"""Learning records, placement history and account recovery."""
from alembic import op

revision = "0003"
down_revision = "0002"


def upgrade():
    op.execute('\nCREATE TABLE password_resets (\n\tuser_id VARCHAR(36) NOT NULL, \n\ttoken_hash VARCHAR(64) NOT NULL, \n\texpires_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tused BOOLEAN NOT NULL, \n\tid VARCHAR(36) NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(user_id) REFERENCES users (id), \n\tUNIQUE (token_hash)\n)\n\n')
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON password_resets TO portal_app")
    op.execute("\nCREATE TABLE grading_policies (\n\tname VARCHAR(160) NOT NULL, \n\tmethod VARCHAR(20) NOT NULL, \n\tscale NUMERIC(8, 2) NOT NULL, \n\tpassing NUMERIC(8, 2) NOT NULL, \n\tattendance_min NUMERIC(5, 2) NOT NULL, \n\tdecimals INTEGER NOT NULL, \n\trecovery VARCHAR(20) NOT NULL, \n\tconcepts JSON NOT NULL, \n\tinstitution_id VARCHAR(36) NOT NULL, \n\tschool_id VARCHAR(36) NOT NULL, \n\tid VARCHAR(36) NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (institution_id, school_id, id), \n\tFOREIGN KEY(institution_id, school_id) REFERENCES schools (institution_id, id), \n\tCHECK (method IN ('simple','weighted','points','concepts')), \n\tCHECK (scale > 0 AND passing >= 0 AND passing <= scale), \n\tCHECK (attendance_min BETWEEN 0 AND 100 AND decimals BETWEEN 0 AND 2), \n\tCHECK (recovery IN ('none','best','replace','average'))\n)\n\n")
    op.execute('CREATE INDEX ix_grading_policies_institution_id ON grading_policies (institution_id)')
    op.execute("ALTER TABLE grading_policies ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE grading_policies FORCE ROW LEVEL SECURITY")
    op.execute("CREATE POLICY tenant_isolation ON grading_policies USING (institution_id = nullif(current_setting('app.institution_id', true), '')) WITH CHECK (institution_id = nullif(current_setting('app.institution_id', true), ''))")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON grading_policies TO portal_app")
    op.execute('\nCREATE TABLE enrollment_movements (\n\tenrollment_id VARCHAR(36) NOT NULL, \n\taction VARCHAR(20) NOT NULL, \n\treason VARCHAR(1000) NOT NULL, \n\tdate DATE NOT NULL, \n\tclass_id VARCHAR(36) NOT NULL, \n\tinstitution_id VARCHAR(36) NOT NULL, \n\tschool_id VARCHAR(36) NOT NULL, \n\tid VARCHAR(36) NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (institution_id, school_id, id), \n\tFOREIGN KEY(institution_id, school_id) REFERENCES schools (institution_id, id), \n\tFOREIGN KEY(institution_id, school_id, enrollment_id) REFERENCES enrollments (institution_id, school_id, id), \n\tFOREIGN KEY(institution_id, school_id, class_id) REFERENCES classes (institution_id, school_id, id)\n)\n\n')
    op.execute('CREATE INDEX ix_enrollment_movements_institution_id ON enrollment_movements (institution_id)')
    op.execute("ALTER TABLE enrollment_movements ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE enrollment_movements FORCE ROW LEVEL SECURITY")
    op.execute("CREATE POLICY tenant_isolation ON enrollment_movements USING (institution_id = nullif(current_setting('app.institution_id', true), '')) WITH CHECK (institution_id = nullif(current_setting('app.institution_id', true), ''))")
    op.execute("GRANT SELECT, INSERT ON enrollment_movements TO portal_app")
    op.execute("\nCREATE TABLE journals (\n\tassignment_id VARCHAR(36) NOT NULL, \n\tterm_id VARCHAR(36) NOT NULL, \n\tpolicy_id VARCHAR(36) NOT NULL, \n\tstatus VARCHAR(20) NOT NULL, \n\tversion INTEGER NOT NULL, \n\tinstitution_id VARCHAR(36) NOT NULL, \n\tschool_id VARCHAR(36) NOT NULL, \n\tid VARCHAR(36) NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (institution_id, school_id, id), \n\tFOREIGN KEY(institution_id, school_id) REFERENCES schools (institution_id, id), \n\tFOREIGN KEY(institution_id, school_id, assignment_id) REFERENCES assignments (institution_id, school_id, id), \n\tFOREIGN KEY(institution_id, school_id, term_id) REFERENCES academic_terms (institution_id, school_id, id), \n\tFOREIGN KEY(institution_id, school_id, policy_id) REFERENCES grading_policies (institution_id, school_id, id), \n\tUNIQUE (institution_id, school_id, assignment_id, term_id), \n\tCHECK (status IN ('draft','closed','published')), \n\tCHECK (version > 0)\n)\n\n")
    op.execute('CREATE INDEX ix_journals_institution_id ON journals (institution_id)')
    op.execute("ALTER TABLE journals ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE journals FORCE ROW LEVEL SECURITY")
    op.execute("CREATE POLICY tenant_isolation ON journals USING (institution_id = nullif(current_setting('app.institution_id', true), '')) WITH CHECK (institution_id = nullif(current_setting('app.institution_id', true), ''))")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON journals TO portal_app")
    op.execute('\nCREATE TABLE placements (\n\tenrollment_id VARCHAR(36) NOT NULL, \n\tclass_id VARCHAR(36) NOT NULL, \n\tstart_date DATE NOT NULL, \n\tend_date DATE, \n\tinstitution_id VARCHAR(36) NOT NULL, \n\tschool_id VARCHAR(36) NOT NULL, \n\tid VARCHAR(36) NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (institution_id, school_id, id), \n\tFOREIGN KEY(institution_id, school_id) REFERENCES schools (institution_id, id), \n\tFOREIGN KEY(institution_id, school_id, enrollment_id) REFERENCES enrollments (institution_id, school_id, id), \n\tFOREIGN KEY(institution_id, school_id, class_id) REFERENCES classes (institution_id, school_id, id), \n\tCHECK (end_date IS NULL OR end_date > start_date)\n)\n\n')
    op.execute('CREATE INDEX ix_placements_institution_id ON placements (institution_id)')
    op.execute("ALTER TABLE placements ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE placements FORCE ROW LEVEL SECURITY")
    op.execute("CREATE POLICY tenant_isolation ON placements USING (institution_id = nullif(current_setting('app.institution_id', true), '')) WITH CHECK (institution_id = nullif(current_setting('app.institution_id', true), ''))")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON placements TO portal_app")
    op.execute("\nCREATE TABLE assessments (\n\tjournal_id VARCHAR(36) NOT NULL, \n\tname VARCHAR(160) NOT NULL, \n\tdate DATE NOT NULL, \n\tmaximum NUMERIC(8, 2) NOT NULL, \n\tweight NUMERIC(8, 2) NOT NULL, \n\tkind VARCHAR(20) NOT NULL, \n\tinstitution_id VARCHAR(36) NOT NULL, \n\tschool_id VARCHAR(36) NOT NULL, \n\tid VARCHAR(36) NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (institution_id, school_id, id), \n\tFOREIGN KEY(institution_id, school_id) REFERENCES schools (institution_id, id), \n\tFOREIGN KEY(institution_id, school_id, journal_id) REFERENCES journals (institution_id, school_id, id), \n\tCHECK (maximum > 0 AND weight > 0), \n\tCHECK (kind IN ('regular','recovery'))\n)\n\n")
    op.execute('CREATE INDEX ix_assessments_institution_id ON assessments (institution_id)')
    op.execute("ALTER TABLE assessments ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE assessments FORCE ROW LEVEL SECURITY")
    op.execute("CREATE POLICY tenant_isolation ON assessments USING (institution_id = nullif(current_setting('app.institution_id', true), '')) WITH CHECK (institution_id = nullif(current_setting('app.institution_id', true), ''))")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON assessments TO portal_app")
    op.execute('\nCREATE TABLE lessons (\n\tjournal_id VARCHAR(36) NOT NULL, \n\tdate DATE NOT NULL, \n\tslot INTEGER NOT NULL, \n\tcontent VARCHAR(2000) NOT NULL, \n\tcancelled BOOLEAN NOT NULL, \n\tinstitution_id VARCHAR(36) NOT NULL, \n\tschool_id VARCHAR(36) NOT NULL, \n\tid VARCHAR(36) NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (institution_id, school_id, id), \n\tFOREIGN KEY(institution_id, school_id) REFERENCES schools (institution_id, id), \n\tFOREIGN KEY(institution_id, school_id, journal_id) REFERENCES journals (institution_id, school_id, id), \n\tUNIQUE (institution_id, school_id, journal_id, date, slot), \n\tCHECK (slot BETWEEN 1 AND 12)\n)\n\n')
    op.execute('CREATE INDEX ix_lessons_institution_id ON lessons (institution_id)')
    op.execute("ALTER TABLE lessons ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE lessons FORCE ROW LEVEL SECURITY")
    op.execute("CREATE POLICY tenant_isolation ON lessons USING (institution_id = nullif(current_setting('app.institution_id', true), '')) WITH CHECK (institution_id = nullif(current_setting('app.institution_id', true), ''))")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON lessons TO portal_app")
    op.execute('\nCREATE TABLE publications (\n\tjournal_id VARCHAR(36) NOT NULL, \n\trevision INTEGER NOT NULL, \n\tsnapshot JSON NOT NULL, \n\tpublished_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tinstitution_id VARCHAR(36) NOT NULL, \n\tschool_id VARCHAR(36) NOT NULL, \n\tid VARCHAR(36) NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (institution_id, school_id, id), \n\tFOREIGN KEY(institution_id, school_id) REFERENCES schools (institution_id, id), \n\tFOREIGN KEY(institution_id, school_id, journal_id) REFERENCES journals (institution_id, school_id, id), \n\tUNIQUE (institution_id, school_id, journal_id, revision)\n)\n\n')
    op.execute('CREATE INDEX ix_publications_institution_id ON publications (institution_id)')
    op.execute("ALTER TABLE publications ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE publications FORCE ROW LEVEL SECURITY")
    op.execute("CREATE POLICY tenant_isolation ON publications USING (institution_id = nullif(current_setting('app.institution_id', true), '')) WITH CHECK (institution_id = nullif(current_setting('app.institution_id', true), ''))")
    op.execute("GRANT SELECT, INSERT ON publications TO portal_app")
    op.execute("\nCREATE TABLE attendance (\n\tlesson_id VARCHAR(36) NOT NULL, \n\tstudent_id VARCHAR(36) NOT NULL, \n\tstatus VARCHAR(20) NOT NULL, \n\tinstitution_id VARCHAR(36) NOT NULL, \n\tschool_id VARCHAR(36) NOT NULL, \n\tid VARCHAR(36) NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (institution_id, school_id, id), \n\tFOREIGN KEY(institution_id, school_id) REFERENCES schools (institution_id, id), \n\tFOREIGN KEY(institution_id, school_id, lesson_id) REFERENCES lessons (institution_id, school_id, id), \n\tFOREIGN KEY(institution_id, school_id, student_id) REFERENCES students (institution_id, school_id, id), \n\tUNIQUE (institution_id, school_id, lesson_id, student_id), \n\tCHECK (status IN ('present','absent','excused'))\n)\n\n")
    op.execute('CREATE INDEX ix_attendance_institution_id ON attendance (institution_id)')
    op.execute("ALTER TABLE attendance ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE attendance FORCE ROW LEVEL SECURITY")
    op.execute("CREATE POLICY tenant_isolation ON attendance USING (institution_id = nullif(current_setting('app.institution_id', true), '')) WITH CHECK (institution_id = nullif(current_setting('app.institution_id', true), ''))")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON attendance TO portal_app")
    op.execute('\nCREATE TABLE grades (\n\tassessment_id VARCHAR(36) NOT NULL, \n\tstudent_id VARCHAR(36) NOT NULL, \n\tvalue NUMERIC(8, 2), \n\tinstitution_id VARCHAR(36) NOT NULL, \n\tschool_id VARCHAR(36) NOT NULL, \n\tid VARCHAR(36) NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (institution_id, school_id, id), \n\tFOREIGN KEY(institution_id, school_id) REFERENCES schools (institution_id, id), \n\tFOREIGN KEY(institution_id, school_id, assessment_id) REFERENCES assessments (institution_id, school_id, id), \n\tFOREIGN KEY(institution_id, school_id, student_id) REFERENCES students (institution_id, school_id, id), \n\tUNIQUE (institution_id, school_id, assessment_id, student_id), \n\tCHECK (value IS NULL OR value >= 0)\n)\n\n')
    op.execute('CREATE INDEX ix_grades_institution_id ON grades (institution_id)')
    op.execute("ALTER TABLE grades ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE grades FORCE ROW LEVEL SECURITY")
    op.execute("CREATE POLICY tenant_isolation ON grades USING (institution_id = nullif(current_setting('app.institution_id', true), '')) WITH CHECK (institution_id = nullif(current_setting('app.institution_id', true), ''))")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON grades TO portal_app")
    op.execute("""INSERT INTO placements (id, institution_id, school_id, enrollment_id, class_id, start_date, end_date) SELECT gen_random_uuid()::text, e.institution_id, e.school_id, e.id, e.class_id, y.start_date, CASE WHEN e.status = 'cancelled' THEN y.end_date + 1 ELSE NULL END FROM enrollments e JOIN academic_years y ON y.institution_id=e.institution_id AND y.school_id=e.school_id AND y.year=e.academic_year""")
    op.execute("REVOKE UPDATE, DELETE ON grading_policies FROM portal_app")
    op.execute("""CREATE FUNCTION validate_placement() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE e enrollments%ROWTYPE; c classes%ROWTYPE;
    BEGIN
        SELECT * INTO e FROM enrollments WHERE id=NEW.enrollment_id AND institution_id=NEW.institution_id AND school_id=NEW.school_id FOR UPDATE;
        SELECT * INTO c FROM classes WHERE id=NEW.class_id AND institution_id=NEW.institution_id AND school_id=NEW.school_id;
        IF e.academic_year IS DISTINCT FROM c.academic_year OR EXISTS (
            SELECT 1 FROM placements p WHERE p.enrollment_id=NEW.enrollment_id AND p.id<>NEW.id
            AND daterange(p.start_date,p.end_date,'[)') && daterange(NEW.start_date,NEW.end_date,'[)')) THEN
            RAISE EXCEPTION 'Invalid or overlapping placement' USING ERRCODE='23514';
        END IF;
        RETURN NEW;
    END $$""")
    op.execute("CREATE TRIGGER placement_dates BEFORE INSERT OR UPDATE ON placements FOR EACH ROW EXECUTE FUNCTION validate_placement()")
    op.execute("""CREATE FUNCTION guard_journal_child() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE jid text; state text;
    BEGIN
        IF TG_TABLE_NAME IN ('lessons','assessments') THEN jid := NEW.journal_id;
        ELSIF TG_TABLE_NAME='attendance' THEN SELECT journal_id INTO jid FROM lessons WHERE id=NEW.lesson_id;
        ELSE SELECT journal_id INTO jid FROM assessments WHERE id=NEW.assessment_id;
        END IF;
        SELECT status INTO state FROM journals WHERE id=jid AND institution_id=NEW.institution_id AND school_id=NEW.school_id FOR UPDATE;
        IF state IS DISTINCT FROM 'draft' THEN RAISE EXCEPTION 'Journal is closed' USING ERRCODE='23514'; END IF;
        RETURN NEW;
    END $$""")
    for table in ('lessons','assessments','attendance','grades'):
        op.execute(f"CREATE TRIGGER journal_child BEFORE INSERT OR UPDATE ON {table} FOR EACH ROW EXECUTE FUNCTION guard_journal_child()")
    op.execute("REVOKE DELETE ON lessons, assessments, attendance, grades, placements, journals FROM portal_app")
    op.execute("""CREATE FUNCTION protect_learning_term() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
        IF (NEW.start_date<>OLD.start_date OR NEW.end_date<>OLD.end_date OR NEW.academic_year_id<>OLD.academic_year_id)
        AND EXISTS(SELECT 1 FROM journals WHERE term_id=OLD.id AND institution_id=OLD.institution_id) THEN
            RAISE EXCEPTION 'Term already used in journal' USING ERRCODE='23514';
        END IF; RETURN NEW;
    END $$""")
    op.execute("CREATE TRIGGER learning_term BEFORE UPDATE ON academic_terms FOR EACH ROW EXECUTE FUNCTION protect_learning_term()")

    op.execute('\nCREATE TABLE journal_reopenings (\n\tjournal_id VARCHAR(36) NOT NULL, \n\treason VARCHAR(1000) NOT NULL, \n\tactor_id VARCHAR(36) NOT NULL, \n\toccurred_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tinstitution_id VARCHAR(36) NOT NULL, \n\tschool_id VARCHAR(36) NOT NULL, \n\tid VARCHAR(36) NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (institution_id, school_id, id), \n\tFOREIGN KEY(institution_id, school_id) REFERENCES schools (institution_id, id), \n\tFOREIGN KEY(institution_id, school_id, journal_id) REFERENCES journals (institution_id, school_id, id), \n\tFOREIGN KEY(actor_id) REFERENCES users (id)\n)\n\n')
    op.execute('CREATE INDEX ix_journal_reopenings_institution_id ON journal_reopenings (institution_id)')
    op.execute("ALTER TABLE journal_reopenings ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE journal_reopenings FORCE ROW LEVEL SECURITY")
    op.execute("CREATE POLICY tenant_isolation ON journal_reopenings USING (institution_id = nullif(current_setting('app.institution_id', true), '')) WITH CHECK (institution_id = nullif(current_setting('app.institution_id', true), ''))")
    op.execute("GRANT SELECT, INSERT ON journal_reopenings TO portal_app")


def downgrade():
    op.execute("DROP TRIGGER learning_term ON academic_terms")
    op.execute("DROP FUNCTION protect_learning_term()")
    for table in ('lessons','assessments','attendance','grades'):
        op.execute(f"DROP TRIGGER journal_child ON {table}")
    op.execute("DROP FUNCTION guard_journal_child()")
    op.execute("DROP TRIGGER placement_dates ON placements")
    op.execute("DROP FUNCTION validate_placement()")
    for table in ('journal_reopenings','password_resets','enrollment_movements','placements','publications','grades','attendance','assessments','lessons','journals','grading_policies'):
        op.drop_table(table)
