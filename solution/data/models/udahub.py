import enum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, declarative_base, relationship
from sqlalchemy.sql import func

Base: DeclarativeBase = declarative_base()


class Account(Base):
    __tablename__ = "accounts"

    account_id = Column(String, primary_key=True)
    account_name = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    users = relationship("User", back_populates="account")
    tickets = relationship("Ticket", back_populates="account")
    knowledge_articles = relationship("Knowledge", back_populates="account")


class User(Base):
    __tablename__ = "users"

    user_id = Column(String, primary_key=True)
    account_id = Column(String, ForeignKey("accounts.account_id"), nullable=False)
    external_user_id = Column(String, nullable=False)
    user_name = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    account = relationship("Account", back_populates="users")
    tickets = relationship("Ticket", back_populates="user")

    __table_args__ = (
        UniqueConstraint("account_id", "external_user_id", name="uq_user_external_per_account"),
    )


class Ticket(Base):
    __tablename__ = "tickets"

    ticket_id = Column(String, primary_key=True)
    account_id = Column(String, ForeignKey("accounts.account_id"), nullable=False)
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False)
    channel = Column(String)
    created_at = Column(DateTime, default=func.now())

    account = relationship("Account", back_populates="tickets")
    user = relationship("User", back_populates="tickets")
    ticket_metadata = relationship("TicketMetadata", uselist=False, back_populates="ticket")
    messages = relationship("TicketMessage", back_populates="ticket")


class TicketMetadata(Base):
    __tablename__ = "ticket_metadata"

    ticket_id = Column(String, ForeignKey("tickets.ticket_id"), primary_key=True)
    status = Column(String, nullable=False)
    main_issue_type = Column(String)
    tags = Column(Text)
    urgency = Column(String, default="normal")
    complexity = Column(String, default="low")
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    ticket = relationship("Ticket", back_populates="ticket_metadata")


class RoleEnum(enum.Enum):
    user = "user"
    agent = "agent"
    ai = "ai"
    system = "system"


class TicketMessage(Base):
    __tablename__ = "ticket_messages"

    message_id = Column(String, primary_key=True)
    ticket_id = Column(String, ForeignKey("tickets.ticket_id"), nullable=False)
    role = Column(Enum(RoleEnum, name="role_enum"), nullable=False)
    content = Column(Text)
    created_at = Column(DateTime, default=func.now())

    ticket = relationship("Ticket", back_populates="messages")


class Knowledge(Base):
    __tablename__ = "knowledge"

    article_id = Column(String, primary_key=True)
    account_id = Column(String, ForeignKey("accounts.account_id"), nullable=False)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    tags = Column(Text)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    account = relationship("Account", back_populates="knowledge_articles")


class InteractionHistory(Base):
    __tablename__ = "interaction_history"

    interaction_id = Column(String, primary_key=True)
    ticket_id = Column(String, nullable=False)
    account_id = Column(String, nullable=False)
    external_user_id = Column(String, nullable=False)
    user_message = Column(Text, nullable=False)
    final_response = Column(Text, nullable=False)
    status = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.now())


class LongTermMemory(Base):
    __tablename__ = "long_term_memory"

    memory_id = Column(String, primary_key=True)
    account_id = Column(String, nullable=False)
    external_user_id = Column(String, nullable=False)
    preferences = Column(Text, default="{}")
    recent_issues = Column(Text, default="[]")
    last_resolution = Column(Text, default="")
    resolved_count = Column(Integer, default=0)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("account_id", "external_user_id", name="uq_memory_per_user_account"),
    )
