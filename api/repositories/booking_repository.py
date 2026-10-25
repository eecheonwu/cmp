from sqlalchemy.orm import Session
from sqlalchemy import select
from api.models.booking import Booking


class BookingRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_locked_by_resource_and_slot(self, resource_id: int, slot_start, slot_end):
        stmt = (
            select(Booking)
            .where(
                Booking.resource_id == resource_id,
                Booking.slot_start == slot_start,
                Booking.slot_end == slot_end,
            )
            .with_for_update(nowait=False)
        )
        return self.session.execute(stmt).scalars().all()

    def get_locked_overlapping(self, resource_id: int, slot_start, slot_end):
        stmt = (
            select(Booking)
            .where(
                Booking.resource_id == resource_id,
                Booking.slot_start < slot_end,
                Booking.slot_end > slot_start,
            )
            .with_for_update()
        )
        return self.session.execute(stmt).scalars().all()

    def create(self, booking: Booking):
        self.session.add(booking)
        self.session.flush()
        return booking
