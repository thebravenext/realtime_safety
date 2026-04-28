from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from app.db.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    email = Column(String(120), unique=True, nullable=False, index=True)
    password = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Camera(Base):
    __tablename__ = "cameras"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(120), nullable=False)
    source = Column(Text, nullable=False)
    selected_model = Column(String(50), nullable=False, default="ppe")
    is_active = Column(Boolean, default=False)
    last_status = Column(String(50), default="Stopped")
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class FrameSummary(Base):
    __tablename__ = "frame_summaries"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=False, index=True)
    frame_index = Column(Integer, nullable=False)
    wearing = Column(Integer, default=0)
    not_wearing = Column(Integer, default=0)
    persons = Column(Integer, default=0)
    in_count = Column(Integer, default=0)
    out_count = Column(Integer, default=0)
    inference_ms = Column(Float, default=0.0)


class FrameNotification(Base):
    __tablename__ = "frame_notifications"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=False, index=True)
    frame_index = Column(Integer, nullable=False)
    person_id = Column(Integer, nullable=False, default=0)
    violation_type = Column(String(120), nullable=False)
    message = Column(Text, nullable=False)
    image_url = Column(Text, nullable=True)


class PPEAlertSummary(Base):
    __tablename__ = "ppe_alert_summaries"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=False, index=True)
    hardhat_count = Column(Integer, default=0)
    hardhat_drop = Column(Float, default=0.0)
    vest_count = Column(Integer, default=0)
    vest_drop = Column(Float, default=0.0)
    mask_count = Column(Integer, default=0)
    mask_drop = Column(Float, default=0.0)
    gloves_count = Column(Integer, default=0)
    gloves_drop = Column(Float, default=0.0)


class PersonPPEStatus(Base):
    __tablename__ = "person_ppe_statuses"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=False, index=True)
    frame_index = Column(Integer, nullable=False)
    person_id = Column(Integer, nullable=False)
    person = Column(String(50), default="detected")
    gloves = Column(String(20), default="missing")
    hardhat = Column(String(20), default="missing")
    mask = Column(String(20), default="missing")
    vest = Column(String(20), default="missing")