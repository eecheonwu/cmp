from sqlalchemy.orm import Session
from api.repositories.booking_repository import BookingRepository
from api.models.booking import Booking


class BookingService:
    def __init__(self, session: Session):
        self.session = session
        self.repo = BookingRepository(session)

    def create_booking(self, branch_id: int, resource_id: int, slot_start, slot_end, user_id: int):
        with self.session.begin():
            # Pessimistic lock relevant rows
            locked = self.repo.get_locked_overlapping(resource_id, slot_start, slot_end)
            if locked:
                raise ValueError("Resource already booked for overlapping slot")

            # Additional branch-level lock scope per FR-004/FR-019
            self.repo.get_locked_by_resource_and_slot(resource_id, slot_start, slot_end)

            booking = Booking(
                branch_id=branch_id,
                resource_id=resource_id,
                slot_start=slot_start,
                slot_end=slot_end,
                user_id=user_id,
                status="confirmed",
            )
            self.repo.create(booking)
            return booking

    def validate_and_lock(self, resource_id: int, slot_start, slot_end):
        with self.session.begin():
            locked = self.repo.get_locked_overlapping(resource_id, slot_start, slot_end)
            if locked:
                return False
            return True
