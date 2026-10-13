"""Academic calendars, periods and versioned curricula; preserve existing classes."""
from alembic import op

revision = "0002"
down_revision = "0001"


def upgrade():
    tables = {
        "academic_years": """
            name VARCHAR(160) NOT NULL, year INTEGER NOT NULL,
            start_date DATE NOT NULL, end_date DATE NOT NULL, needs_review BOOLEAN NOT NULL,
            UNIQUE (institution_id, school_id, year),
            CHECK (year BETWEEN 2000 AND 2100), CHECK (start_date <= end_date)
        """,
        "academic_terms": """
            name VARCHAR(160) NOT NULL, academic_year_id VARCHAR(36) NOT NULL,
            sequence INTEGER NOT NULL, start_date DATE NOT NULL, end_date DATE NOT NULL,
            FOREIGN KEY (institution_id, school_id, academic_year_id)
                REFERENCES academic_years (institution_id, school_id, id),
            UNIQUE (institution_id, school_id, academic_year_id, sequence),
            UNIQUE (institution_id, school_id, academic_year_id, name),
            CHECK (sequence BETWEEN 1 AND 24), CHECK (start_date <= end_date)
        """,
        "curricula": """
            name VARCHAR(160) NOT NULL, code VARCHAR(30) NOT NULL, grade_level VARCHAR(60) NOT NULL,
            version INTEGER NOT NULL, status VARCHAR(20) NOT NULL,
            UNIQUE (institution_id, school_id, code, version),
            CHECK (version BETWEEN 1 AND 999), CHECK (status IN ('draft', 'published'))
        """,
        "curriculum_subjects": """
            curriculum_id VARCHAR(36) NOT NULL, subject_id VARCHAR(36) NOT NULL, workload_hours INTEGER NOT NULL,
            FOREIGN KEY (institution_id, school_id, curriculum_id)
                REFERENCES curricula (institution_id, school_id, id),
            FOREIGN KEY (institution_id, school_id, subject_id)
                REFERENCES subjects (institution_id, school_id, id),
            UNIQUE (institution_id, school_id, curriculum_id, subject_id),
            CHECK (workload_hours BETWEEN 1 AND 3000)
        """,
    }
    for table, columns in tables.items():
        op.execute(f"""CREATE TABLE {table} (
            id VARCHAR(36) PRIMARY KEY, institution_id VARCHAR(36) NOT NULL, school_id VARCHAR(36) NOT NULL,
            UNIQUE (institution_id, school_id, id),
            FOREIGN KEY (institution_id, school_id) REFERENCES schools (institution_id, id),
            {columns})""")
        op.execute(f"CREATE INDEX ix_{table}_institution_id ON {table} (institution_id)")

    # Initial dates are placeholders explicitly flagged for institutional review.
    op.execute("""INSERT INTO academic_years (id, institution_id, school_id, name, year, start_date, end_date, needs_review)
        SELECT gen_random_uuid()::text, institution_id, school_id, academic_year::text, academic_year,
               make_date(academic_year, 1, 1), make_date(academic_year, 12, 31), true
        FROM classes GROUP BY institution_id, school_id, academic_year""")
    op.execute("ALTER TABLE classes ADD COLUMN curriculum_id VARCHAR(36)")
    op.execute("""ALTER TABLE classes ADD CONSTRAINT fk_classes_academic_year
        FOREIGN KEY (institution_id, school_id, academic_year)
        REFERENCES academic_years (institution_id, school_id, year)""")
    op.execute("""ALTER TABLE classes ADD CONSTRAINT fk_classes_curriculum
        FOREIGN KEY (institution_id, school_id, curriculum_id)
        REFERENCES curricula (institution_id, school_id, id)""")

    for table in tables:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(f"""CREATE POLICY tenant_isolation ON {table}
            USING (institution_id = nullif(current_setting('app.institution_id', true), ''))
            WITH CHECK (institution_id = nullif(current_setting('app.institution_id', true), ''))""")
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO portal_app")

    op.execute("""CREATE FUNCTION validate_academic_term() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE calendar academic_years%ROWTYPE;
        BEGIN
            SELECT * INTO calendar FROM academic_years
                WHERE id = NEW.academic_year_id AND institution_id = NEW.institution_id AND school_id = NEW.school_id
                FOR UPDATE;
            IF NOT FOUND OR NEW.start_date < calendar.start_date OR NEW.end_date > calendar.end_date THEN
                RAISE EXCEPTION 'Period outside calendar' USING ERRCODE = '23514';
            END IF;
            IF TG_OP = 'UPDATE' AND NEW.academic_year_id <> OLD.academic_year_id THEN
                RAISE EXCEPTION 'Period cannot change year' USING ERRCODE = '23514';
            END IF;
            IF EXISTS (SELECT 1 FROM academic_terms t WHERE t.academic_year_id = NEW.academic_year_id
                AND t.institution_id = NEW.institution_id AND t.school_id = NEW.school_id AND t.id <> NEW.id
                AND ((t.start_date <= NEW.end_date AND t.end_date >= NEW.start_date)
                    OR (t.sequence < NEW.sequence AND t.start_date > NEW.start_date)
                    OR (t.sequence > NEW.sequence AND t.start_date < NEW.start_date))) THEN
                RAISE EXCEPTION 'Period overlap or invalid sequence' USING ERRCODE = '23514';
            END IF;
            RETURN NEW;
        END $$""")
    op.execute("CREATE TRIGGER academic_term_dates BEFORE INSERT OR UPDATE ON academic_terms FOR EACH ROW EXECUTE FUNCTION validate_academic_term()")
    op.execute("""CREATE FUNCTION protect_academic_year() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF NEW.year <> OLD.year OR EXISTS (SELECT 1 FROM academic_terms t
                WHERE t.academic_year_id = OLD.id AND t.institution_id = OLD.institution_id AND t.school_id = OLD.school_id
                AND (t.start_date < NEW.start_date OR t.end_date > NEW.end_date)) THEN
                RAISE EXCEPTION 'Calendar change invalidates history' USING ERRCODE = '23514';
            END IF;
            RETURN NEW;
        END $$""")
    op.execute("CREATE TRIGGER academic_year_history BEFORE UPDATE ON academic_years FOR EACH ROW EXECUTE FUNCTION protect_academic_year()")
    op.execute("""CREATE FUNCTION protect_curriculum() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF OLD.status = 'published' THEN
                RAISE EXCEPTION 'Published curriculum is immutable' USING ERRCODE = '23514';
            END IF;
            IF TG_OP = 'UPDATE' AND (NEW.code <> OLD.code OR NEW.version <> OLD.version) THEN
                RAISE EXCEPTION 'Curriculum identity is immutable' USING ERRCODE = '23514';
            END IF;
            IF TG_OP = 'UPDATE' AND NEW.status = 'published' AND NOT EXISTS (
                SELECT 1 FROM curriculum_subjects c WHERE c.curriculum_id = OLD.id
                AND c.institution_id = OLD.institution_id AND c.school_id = OLD.school_id) THEN
                RAISE EXCEPTION 'Empty curriculum cannot be published' USING ERRCODE = '23514';
            END IF;
            IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
            RETURN NEW;
        END $$""")
    op.execute("CREATE TRIGGER curriculum_history BEFORE UPDATE OR DELETE ON curricula FOR EACH ROW EXECUTE FUNCTION protect_curriculum()")
    op.execute("""CREATE FUNCTION protect_curriculum_subject() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE target curriculum_subjects%ROWTYPE; state VARCHAR(20);
        BEGIN
            IF TG_OP = 'DELETE' THEN target := OLD; ELSE target := NEW; END IF;
            IF TG_OP = 'UPDATE' AND NEW.curriculum_id <> OLD.curriculum_id THEN
                RAISE EXCEPTION 'Component cannot change curriculum' USING ERRCODE = '23514';
            END IF;
            SELECT status INTO state FROM curricula WHERE id = target.curriculum_id
                AND institution_id = target.institution_id AND school_id = target.school_id FOR UPDATE;
            IF state IS DISTINCT FROM 'draft' THEN
                RAISE EXCEPTION 'Published curriculum components are immutable' USING ERRCODE = '23514';
            END IF;
            IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
            RETURN NEW;
        END $$""")
    op.execute("CREATE TRIGGER curriculum_subject_history BEFORE INSERT OR UPDATE OR DELETE ON curriculum_subjects FOR EACH ROW EXECUTE FUNCTION protect_curriculum_subject()")


def downgrade():
    for table, trigger, function in [
        ("curriculum_subjects", "curriculum_subject_history", "protect_curriculum_subject"),
        ("curricula", "curriculum_history", "protect_curriculum"),
        ("academic_years", "academic_year_history", "protect_academic_year"),
        ("academic_terms", "academic_term_dates", "validate_academic_term"),
    ]:
        op.execute(f"DROP TRIGGER {trigger} ON {table}")
        op.execute(f"DROP FUNCTION {function}()")
    op.drop_constraint("fk_classes_curriculum", "classes", type_="foreignkey")
    op.drop_constraint("fk_classes_academic_year", "classes", type_="foreignkey")
    op.drop_column("classes", "curriculum_id")
    for table in ["curriculum_subjects", "curricula", "academic_terms", "academic_years"]:
        op.drop_table(table)
