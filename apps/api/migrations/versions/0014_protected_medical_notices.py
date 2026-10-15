"""Encrypt medical authorization content while preserving issued wording."""

import os
from alembic import op
from sqlalchemy import text
from cryptography.fernet import Fernet

revision = "0014"
down_revision = "0013"


def convert(encrypt):
    rows = (
        op.get_bind()
        .execute(
            text(
                "SELECT id,title,body FROM notices WHERE purpose='medication'"
                if encrypt
                else "SELECT id,title,body FROM notices WHERE body_encrypted=true"
            )
        )
        .mappings()
        .all()
    )
    if not rows:
        return
    key = os.environ.get("APP_ENCRYPTION_KEY")
    if not key:
        raise RuntimeError(
            "APP_ENCRYPTION_KEY is required to migrate existing protected notices."
        )
    cipher = Fernet(key.encode())
    op.execute("ALTER TABLE notices DISABLE TRIGGER issued_content_guard")
    for row in rows:
        title = (
            cipher.encrypt(row["title"].encode()).decode()
            if encrypt
            else cipher.decrypt(row["title"].encode()).decode()
        )
        body = (
            cipher.encrypt(row["body"].encode()).decode()
            if encrypt
            else cipher.decrypt(row["body"].encode()).decode()
        )
        op.get_bind().execute(
            text(
                "UPDATE notices SET title=:title,body=:body,body_encrypted=:encrypted WHERE id=:id"
            ),
            {"title": title, "body": body, "encrypted": encrypt, "id": row["id"]},
        )
    op.execute("ALTER TABLE notices ENABLE TRIGGER issued_content_guard")


def upgrade():
    op.execute("ALTER TABLE notices ALTER COLUMN title TYPE VARCHAR(1000)")
    op.execute("ALTER TABLE notices ALTER COLUMN body TYPE VARCHAR(40000)")
    op.execute(
        "ALTER TABLE notices ADD COLUMN body_encrypted BOOLEAN NOT NULL DEFAULT false"
    )
    convert(True)
    op.execute("ALTER TABLE notices ALTER COLUMN body_encrypted DROP DEFAULT")


def downgrade():
    convert(False)
    op.drop_column("notices", "body_encrypted")
    op.execute("ALTER TABLE notices ALTER COLUMN title TYPE VARCHAR(160)")
    op.execute("ALTER TABLE notices ALTER COLUMN body TYPE VARCHAR(6000)")
