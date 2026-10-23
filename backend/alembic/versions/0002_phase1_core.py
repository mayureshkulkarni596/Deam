from alembic import op
import sqlalchemy as sa

revision = "0002_phase1_core"
down_revision = "0001_initial_users"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table("visitors",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("resident_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False), sa.Column("phone", sa.String(32), nullable=False),
        sa.Column("category", sa.String(20), nullable=False), sa.Column("credential_mode", sa.String(20), nullable=False),
        sa.Column("pin_hash", sa.String(255)), sa.Column("secret_enc", sa.Text()),
        sa.Column("auto_open", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("schedule_json", sa.JSON()), sa.Column("outside_schedule_action", sa.String(10), nullable=False, server_default="ASK"),
        sa.Column("valid_from", sa.DateTime(timezone=True)), sa.Column("valid_until", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(20), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index("ix_visitors_resident_id", "visitors", ["resident_id"])
    op.create_index("ix_visitors_status", "visitors", ["status"])
    op.create_table("face_embeddings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("visitor_id", sa.Integer(), sa.ForeignKey("visitors.id", ondelete="CASCADE"), nullable=False),
        sa.Column("embedding", sa.LargeBinary(), nullable=False), sa.Column("model_version", sa.String(80), nullable=False),
        sa.Column("quality_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index("ix_face_embeddings_visitor_id", "face_embeddings", ["visitor_id"])
    op.create_table("kiosks",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("name", sa.String(100), nullable=False),
        sa.Column("api_key_hash", sa.String(255), nullable=False), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_seen_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_table("gate_requests",
        sa.Column("id", sa.String(36), primary_key=True), sa.Column("flat_no", sa.String(30), nullable=False),
        sa.Column("resident_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("visitor_id", sa.Integer(), sa.ForeignKey("visitors.id", ondelete="SET NULL")),
        sa.Column("mode", sa.String(20), nullable=False), sa.Column("visitor_name", sa.String(120), nullable=False),
        sa.Column("purpose", sa.String(300)), sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("deny_reason", sa.String(50)), sa.Column("pin_valid", sa.Boolean()), sa.Column("face_score", sa.Float()),
        sa.Column("face_mismatch", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("snapshot_path", sa.String(500)), sa.Column("decision_source", sa.String(20), nullable=False, server_default="SYSTEM"),
        sa.Column("decided_by", sa.Integer(), sa.ForeignKey("users.id")), sa.Column("kiosk_id", sa.Integer(), sa.ForeignKey("kiosks.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True)), sa.Column("decided_at", sa.DateTime(timezone=True)))
    for column in ("resident_id", "visitor_id", "kiosk_id"):
        op.create_index(f"ix_gate_requests_{column}", "gate_requests", [column])
    op.create_index("ix_gate_requests_status_created_at", "gate_requests", ["status", "created_at"])
    op.create_index("ix_gate_requests_flat_no", "gate_requests", ["flat_no"])
    op.create_table("login_attempts",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("key", sa.String(200), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index("ix_login_attempts_key", "login_attempts", ["key"])
    op.create_table("audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("actor_type", sa.String(20), nullable=False),
        sa.Column("actor_id", sa.String(80)), sa.Column("action", sa.String(80), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False), sa.Column("entity_id", sa.String(80)),
        sa.Column("details_json", sa.JSON(), nullable=False), sa.Column("ip", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])

def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_index("ix_login_attempts_key", table_name="login_attempts")
    op.drop_table("login_attempts")
    op.drop_index("ix_gate_requests_flat_no", table_name="gate_requests")
    op.drop_index("ix_gate_requests_status_created_at", table_name="gate_requests")
    for column in ("resident_id", "visitor_id", "kiosk_id"):
        op.drop_index(f"ix_gate_requests_{column}", table_name="gate_requests")
    op.drop_table("gate_requests")
    op.drop_table("kiosks")
    op.drop_index("ix_face_embeddings_visitor_id", table_name="face_embeddings")
    op.drop_table("face_embeddings")
    op.drop_index("ix_visitors_status", table_name="visitors")
    op.drop_index("ix_visitors_resident_id", table_name="visitors")
    op.drop_table("visitors")
