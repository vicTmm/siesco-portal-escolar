"""Database guards for eligible students, dates and grade bounds."""
from alembic import op
revision='0005'
down_revision='0004'


def upgrade():
    op.execute("""CREATE FUNCTION validate_learning_record() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE jid text; classid text; day date; maximum numeric; cancelled boolean;
    BEGIN
        IF TG_TABLE_NAME IN ('lessons','assessments') THEN
            jid:=NEW.journal_id;day:=NEW.date;
        ELSIF TG_TABLE_NAME='attendance' THEN
            SELECT l.journal_id,l.date,l.cancelled INTO jid,day,cancelled FROM lessons l WHERE l.id=NEW.lesson_id;
            IF cancelled IS DISTINCT FROM false THEN RAISE EXCEPTION 'Cancelled lesson' USING ERRCODE='23514'; END IF;
        ELSE
            SELECT a.journal_id,a.date,a.maximum INTO jid,day,maximum FROM assessments a WHERE a.id=NEW.assessment_id;
            IF NEW.value>maximum THEN RAISE EXCEPTION 'Grade exceeds maximum' USING ERRCODE='23514'; END IF;
        END IF;
        SELECT a.class_id INTO classid FROM journals j JOIN assignments a ON a.id=j.assignment_id
          JOIN academic_terms t ON t.id=j.term_id
          WHERE j.id=jid AND j.institution_id=NEW.institution_id AND j.school_id=NEW.school_id
          AND day BETWEEN t.start_date AND t.end_date;
        IF NOT FOUND THEN RAISE EXCEPTION 'Record outside term' USING ERRCODE='23514'; END IF;
        IF TG_TABLE_NAME IN ('attendance','grades') THEN
          IF NOT EXISTS(
          SELECT 1 FROM placements p JOIN enrollments e ON e.id=p.enrollment_id
          WHERE e.student_id=NEW.student_id AND p.class_id=classid AND p.institution_id=NEW.institution_id
          AND p.school_id=NEW.school_id AND p.start_date<=day AND (p.end_date IS NULL OR p.end_date>day)) THEN
          RAISE EXCEPTION 'Student not eligible on date' USING ERRCODE='23514';
          END IF;
        END IF;
        RETURN NEW;
    END $$""")
    for table in ('lessons','assessments','attendance','grades'):
        op.execute(f'CREATE TRIGGER learning_record BEFORE INSERT OR UPDATE ON {table} FOR EACH ROW EXECUTE FUNCTION validate_learning_record()')
    op.execute("""CREATE FUNCTION guard_annual_terms() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE target text;
    BEGIN
        IF TG_OP='DELETE' THEN target:=OLD.academic_year_id; ELSE target:=NEW.academic_year_id; END IF;
        IF EXISTS(SELECT 1 FROM annual_policies WHERE academic_year_id=target AND institution_id=COALESCE(NEW.institution_id,OLD.institution_id)) THEN
            RAISE EXCEPTION 'Annual policy already fixes terms' USING ERRCODE='23514';
        END IF;
        IF TG_OP='DELETE' THEN RETURN OLD; END IF; RETURN NEW;
    END $$""")
    op.execute('CREATE TRIGGER annual_terms BEFORE INSERT OR UPDATE OR DELETE ON academic_terms FOR EACH ROW EXECUTE FUNCTION guard_annual_terms()')


def downgrade():
    op.execute('DROP TRIGGER annual_terms ON academic_terms')
    op.execute('DROP FUNCTION guard_annual_terms()')
    for table in ('lessons','assessments','attendance','grades'):
        op.execute(f'DROP TRIGGER learning_record ON {table}')
    op.execute('DROP FUNCTION validate_learning_record()')
