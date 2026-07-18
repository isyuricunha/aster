from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models import TimestampMixin


class AgentMessageDispatch(TimestampMixin, Base):
    __tablename__ = "agent_message_dispatches"
    __table_args__ = (
        UniqueConstraint(
            "rule_id",
            "message_id",
            name="uq_agent_message_dispatch",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    rule_id: Mapped[UUID] = mapped_column(
        ForeignKey("agent_communication_rules.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    message_id: Mapped[UUID] = mapped_column(
        ForeignKey("communication_messages.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    run_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
