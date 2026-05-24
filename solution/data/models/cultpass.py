from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase, declarative_base, relationship
from sqlalchemy.sql import func

Base: DeclarativeBase = declarative_base()


class User(Base):
    __tablename__ = "users"

    user_id = Column(String, primary_key=True)
    full_name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    is_blocked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    subscription = relationship("Subscription", back_populates="user", uselist=False)
    reservations = relationship("Reservation", back_populates="user")


class Subscription(Base):
    __tablename__ = "subscriptions"

    subscription_id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.user_id"), unique=True, nullable=False)
    status = Column(String, nullable=False)
    tier = Column(String, nullable=False)
    monthly_quota = Column(Integer, nullable=False)
    started_at = Column(DateTime, default=func.now(), nullable=False)
    ended_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="subscription")


class Experience(Base):
    __tablename__ = "experiences"

    experience_id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    location = Column(String, nullable=False)
    when = Column(DateTime, nullable=False)
    slots_available = Column(Integer, nullable=False)
    is_premium = Column(Boolean, nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    reservations = relationship("Reservation", back_populates="experience")


class Reservation(Base):
    __tablename__ = "reservations"

    reservation_id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False)
    experience_id = Column(String, ForeignKey("experiences.experience_id"), nullable=False)
    status = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="reservations")
    experience = relationship("Experience", back_populates="reservations")
