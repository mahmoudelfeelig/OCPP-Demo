"""add station authentication and station-scoped message identity

Revision ID: 0002_station_auth
Revises: 0001_initial_schema
Create Date: 2026-06-28 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0002_station_auth"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("stations", sa.Column("ocpp_token_hash", sa.String(length=64), nullable=True))
    op.add_column("meter_values", sa.Column("measurand", sa.String(length=64), nullable=True))
    unique_constraints = sa.inspect(op.get_bind()).get_unique_constraints("ocpp_messages")
    message_id_constraint = next(
        (
            constraint["name"]
            for constraint in unique_constraints
            if constraint.get("column_names") == ["message_id"]
        ),
        None,
    )
    if message_id_constraint is None:
        raise RuntimeError("Could not locate the existing OCPP message-id unique constraint")
    op.drop_constraint(message_id_constraint, "ocpp_messages", type_="unique")
    op.create_unique_constraint(
        "uq_ocpp_message_station_message_id",
        "ocpp_messages",
        ["station_id", "message_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_ocpp_message_station_message_id", "ocpp_messages", type_="unique")
    op.create_unique_constraint("ocpp_messages_message_id_key", "ocpp_messages", ["message_id"])
    op.drop_column("meter_values", "measurand")
    op.drop_column("stations", "ocpp_token_hash")
