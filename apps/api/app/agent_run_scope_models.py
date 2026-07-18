from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models import TimestampMixin


class AgentRunContextScope(TimestampMixin, Base):
    __tablename__ = "agent_run_context_scopes"

    run_id: Mapped[UUID] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="CASCADE"), primary_key=True
    )
    persona_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("personas.id", ondelete="SET NULL"), nullable=True
    )
    memory_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    rag_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)


class AgentRunToolScope(TimestampMixin, Base):
    __tablename__ = "agent_run_tool_scopes"
    __table_args__ = (
        UniqueConstraint("run_id", "tool_id", name="uq_agent_run_tool_scope"),
        CheckConstraint(
            "approval_policy IN ('always', 'tool_default', 'never')",
            name="ck_agent_run_tool_scopes_approval",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    tool_id: Mapped[UUID] = mapped_column(
        ForeignKey("mcp_tools.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    approval_policy: Mapped[str] = mapped_column(String(24), nullable=False)


class AgentRunCommunicationScope(TimestampMixin, Base):
    __tablename__ = "agent_run_communication_scopes"
    __table_args__ = (
        UniqueConstraint("run_id", "account_id", name="uq_agent_run_communication_scope"),
        CheckConstraint(
            "reply_approval_policy IN ('always', 'never')",
            name="ck_agent_run_communication_reply_approval",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    account_id: Mapped[UUID] = mapped_column(
        ForeignKey("communication_accounts.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    allow_read: Mapped[bool] = mapped_column(Boolean, nullable=False)
    allow_reply: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reply_approval_policy: Mapped[str] = mapped_column(String(16), nullable=False)


class AgentRunKnowledgeScope(TimestampMixin, Base):
    __tablename__ = "agent_run_knowledge_scopes"
    __table_args__ = (
        UniqueConstraint("run_id", "collection_id", name="uq_agent_run_knowledge_scope"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    collection_id: Mapped[UUID] = mapped_column(
        ForeignKey("knowledge_collections.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
