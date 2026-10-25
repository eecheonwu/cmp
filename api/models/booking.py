from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from api.database import Base


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False)
    resource_id = Column(Integer, ForeignKey("resources.id"), nullable=False)
    slot_start = Column(DateTime(timezone=True), nullable=False)
    slot_end = Column(DateTime(timezone=True), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String(32), nullable=False, default="confirmed")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("resource_id", "slot_start", "slot_end", name="uq_booking_resource_slot"),
        Index("ix_booking_branch_resource_slot", "branch_id", "resource_id", "slot_start", "slot_end"),
    )

    def __repr__(self):
        return f"<Booking id={self.id} resource_id={self.resource_id} slot={self.slot_start}-{self.slot_end}>"
