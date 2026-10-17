"""Private prepaid ledgers and inventory."""

from alembic import op

revision = "0012"
down_revision = "0011"


def upgrade():
    op.execute(
        "\nCREATE TABLE inventory_items (\n\tchannel VARCHAR(20) NOT NULL, \n\tcode VARCHAR(60) NOT NULL, \n\tname VARCHAR(160) NOT NULL, \n\tprice_cents INTEGER NOT NULL, \n\tstock INTEGER NOT NULL, \n\ttags JSON NOT NULL, \n\tactive BOOLEAN NOT NULL, \n\tversion INTEGER NOT NULL, \n\tinstitution_id VARCHAR(36) NOT NULL, \n\tschool_id VARCHAR(36) NOT NULL, \n\tid VARCHAR(36) NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (institution_id, school_id, id), \n\tFOREIGN KEY(institution_id, school_id) REFERENCES schools (institution_id, id), \n\tUNIQUE (institution_id, school_id, channel, code), \n\tCHECK (channel IN ('canteen','store')), \n\tCHECK (price_cents>0 AND price_cents<=10000000 AND stock>=0 AND stock<=1000000 AND version>0)\n)\n\n"
    )
    op.execute(
        "CREATE INDEX ix_inventory_items_institution_id ON inventory_items (institution_id)"
    )
    op.execute("ALTER TABLE inventory_items ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE inventory_items FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON inventory_items USING (institution_id = nullif(current_setting('app.institution_id', true), '')) WITH CHECK (institution_id = nullif(current_setting('app.institution_id', true), ''))"
    )
    op.execute("GRANT SELECT, INSERT, UPDATE ON inventory_items TO portal_app")
    op.execute(
        "\nCREATE TABLE wallet_policies (\n\tstudent_id VARCHAR(36) NOT NULL, \n\tencrypted BYTEA NOT NULL, \n\tversion INTEGER NOT NULL, \n\tinstitution_id VARCHAR(36) NOT NULL, \n\tschool_id VARCHAR(36) NOT NULL, \n\tid VARCHAR(36) NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (institution_id, school_id, id), \n\tFOREIGN KEY(institution_id, school_id) REFERENCES schools (institution_id, id), \n\tFOREIGN KEY(institution_id, school_id, student_id) REFERENCES students (institution_id, school_id, id), \n\tUNIQUE (institution_id, school_id, student_id), \n\tCHECK (version>0)\n)\n\n"
    )
    op.execute(
        "CREATE INDEX ix_wallet_policies_institution_id ON wallet_policies (institution_id)"
    )
    op.execute("ALTER TABLE wallet_policies ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE wallet_policies FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON wallet_policies USING (institution_id = nullif(current_setting('app.institution_id', true), '')) WITH CHECK (institution_id = nullif(current_setting('app.institution_id', true), ''))"
    )
    op.execute("GRANT SELECT, INSERT, UPDATE ON wallet_policies TO portal_app")
    op.execute(
        "\nCREATE TABLE wallet_entries (\n\tstudent_id VARCHAR(36) NOT NULL, \n\tactor_id VARCHAR(36) NOT NULL, \n\tkey VARCHAR(36) NOT NULL, \n\tpayload_hash VARCHAR(64) NOT NULL, \n\tkind VARCHAR(20) NOT NULL, \n\tchannel VARCHAR(20), \n\tamount_cents INTEGER NOT NULL, \n\tnote VARCHAR(1000) NOT NULL, \n\tlines JSON NOT NULL, \n\treverses_id VARCHAR(36), \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tinstitution_id VARCHAR(36) NOT NULL, \n\tschool_id VARCHAR(36) NOT NULL, \n\tid VARCHAR(36) NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (institution_id, school_id, id), \n\tFOREIGN KEY(institution_id, school_id) REFERENCES schools (institution_id, id), \n\tFOREIGN KEY(institution_id, school_id, student_id) REFERENCES students (institution_id, school_id, id), \n\tFOREIGN KEY(institution_id, school_id, reverses_id) REFERENCES wallet_entries (institution_id, school_id, id), \n\tUNIQUE (institution_id, school_id, key), \n\tUNIQUE (institution_id, school_id, reverses_id), \n\tCHECK (kind IN ('credit','debit','refund')), \n\tCHECK (amount_cents>0 AND amount_cents<=1000000000), \n\tFOREIGN KEY(actor_id) REFERENCES users (id)\n)\n\n"
    )
    op.execute(
        "CREATE INDEX ix_wallet_entries_institution_id ON wallet_entries (institution_id)"
    )
    op.execute(
        "CREATE INDEX ix_wallet_scope_student_date ON wallet_entries (institution_id, school_id, student_id, created_at)"
    )
    op.execute("ALTER TABLE wallet_entries ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE wallet_entries FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON wallet_entries USING (institution_id = nullif(current_setting('app.institution_id', true), '')) WITH CHECK (institution_id = nullif(current_setting('app.institution_id', true), ''))"
    )
    op.execute("GRANT SELECT, INSERT ON wallet_entries TO portal_app")
    op.execute(
        "\nCREATE TABLE store_orders (\n\tentry_id VARCHAR(36) NOT NULL, \n\tstatus VARCHAR(20) NOT NULL, \n\tversion INTEGER NOT NULL, \n\tinstitution_id VARCHAR(36) NOT NULL, \n\tschool_id VARCHAR(36) NOT NULL, \n\tid VARCHAR(36) NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (institution_id, school_id, id), \n\tFOREIGN KEY(institution_id, school_id) REFERENCES schools (institution_id, id), \n\tFOREIGN KEY(institution_id, school_id, entry_id) REFERENCES wallet_entries (institution_id, school_id, id), \n\tUNIQUE (institution_id, school_id, entry_id), \n\tCHECK (status IN ('placed','delivered','cancelled')), \n\tCHECK (version>0)\n)\n\n"
    )
    op.execute(
        "CREATE INDEX ix_store_orders_institution_id ON store_orders (institution_id)"
    )
    op.execute("ALTER TABLE store_orders ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE store_orders FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON store_orders USING (institution_id = nullif(current_setting('app.institution_id', true), '')) WITH CHECK (institution_id = nullif(current_setting('app.institution_id', true), ''))"
    )
    op.execute("GRANT SELECT, INSERT, UPDATE ON store_orders TO portal_app")


def downgrade():
    op.drop_table("store_orders")
    op.drop_table("wallet_entries")
    op.drop_table("wallet_policies")
    op.drop_table("inventory_items")
