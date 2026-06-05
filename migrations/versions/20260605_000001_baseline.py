"""Baseline schema for Machinery Barage Group.

Revision ID: 20260605_000001
Revises:
Create Date: 2026-06-05 12:15:00
"""

from alembic import op

from app import db


revision = "20260605_000001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    db.metadata.create_all(bind=op.get_bind())


def downgrade():
    db.metadata.drop_all(bind=op.get_bind())
