"""
CMP Database Seed Script.

Creates initial users and data for development.
Run with: python seed.py
"""
import asyncio
import sys
from datetime import datetime, timedelta, timezone, date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from core.config import settings
from services.auth_service import hash_password


async def seed():
    """Seed the database with initial users and data."""
    database_url = settings.database_url_async
    print(f"Connecting to database...")
    
    engine = create_async_engine(database_url, echo=True)
    
    async with engine.begin() as conn:
        # Ensure all existing seeded users are marked email verified
        await conn.execute(text("UPDATE users SET is_email_verified = true WHERE is_email_verified IS FALSE OR is_email_verified IS NULL"))

        # Check if users already exist
        result = await conn.execute(text("SELECT COUNT(*) FROM users"))
        user_count = result.scalar_one()
        
        # Create staff users if not exist
        if user_count == 0:
            staff_users = [
                {
                    "phone_number": "+2348000000001",
                    "email": "admin@example.com",
                    "password": "admin123",
                    "role": "admin",
                },
                {
                    "phone_number": "+2348000000002",
                    "email": "staff@example.com",
                    "password": "password123",
                    "role": "receptionist",
                },
                {
                    "phone_number": "+2348000000003",
                    "email": "doctor@example.com",
                    "password": "doctor123",
                    "role": "doctor",
                },
                {
                    "phone_number": "+2348000000004",
                    "email": "manager@example.com",
                    "password": "manager123",
                    "role": "manager",
                },
            ]
            
            for user in staff_users:
                password_hash = hash_password(user["password"])
                await conn.execute(
                    text(
                        """
                        INSERT INTO users (id, phone_number, email, password_hash, role, is_email_verified, created_at, updated_at)
                        VALUES (gen_random_uuid(), :phone, :email, :password_hash, :role, true, NOW(), NOW())
                        """
                    ),
                    {
                        "phone": user["phone_number"],
                        "email": user["email"],
                        "password_hash": password_hash,
                        "role": user["role"],
                    },
                )
                print(f"  Created {user['role']} user: {user['email']}")
        
        # Create a patient user if not exists
        result = await conn.execute(text("SELECT id FROM users WHERE email = 'patient@example.com'"))
        patient_user = result.scalar_one_or_none()
        if not patient_user:
            patient_password_hash = hash_password("patient123")
            await conn.execute(
                text(
                    """
                    INSERT INTO users (id, phone_number, email, password_hash, role, is_email_verified, created_at, updated_at)
                    VALUES (gen_random_uuid(), :phone, :email, :password_hash, :role, true, NOW(), NOW())
                    """
                ),
                {
                    "phone": "+2348000000005",
                    "email": "patient@example.com",
                    "password_hash": patient_password_hash,
                    "role": "patient",
                },
            )
            print(f"  Created patient user: patient@example.com")
        
        # Get the doctor and patient IDs for related data
        result = await conn.execute(text("SELECT id FROM users WHERE email = 'doctor@example.com'"))
        doctor_id = result.scalar_one_or_none()
        
        result = await conn.execute(text("SELECT id FROM users WHERE email = 'patient@example.com'"))
        patient_id = result.scalar_one_or_none()
        
        # Create doctor availability if not exists
        if doctor_id:
            result = await conn.execute(
                text("SELECT COUNT(*) FROM doctor_availability WHERE doctor_id = :doctor_id"),
                {"doctor_id": doctor_id}
            )
            if result.scalar_one() == 0:
                # Create availability for next Monday 9am-5pm
                next_monday = datetime.now(timezone.utc) + timedelta(days=(7 - datetime.now().weekday()))
                next_monday = next_monday.replace(hour=9, minute=0, second=0, microsecond=0)
                
                await conn.execute(
                    text(
                        """
                        INSERT INTO doctor_availability (id, doctor_id, branch_id, start_datetime, end_datetime, is_cancelled, created_at, updated_at)
                        VALUES (gen_random_uuid(), :doctor_id, :branch_id, :start, :end, false, NOW(), NOW())
                        """
                    ),
                    {
                        "doctor_id": doctor_id,
                        "branch_id": "main",
                        "start": next_monday,
                        "end": next_monday + timedelta(hours=8),
                    },
                )
                print(f"  Created doctor availability for doctor@example.com")
        
        # Create patient profile if not exists
        if patient_id:
            result = await conn.execute(
                text("SELECT COUNT(*) FROM patient_profiles WHERE user_id = :user_id"),
                {"user_id": patient_id}
            )
            if result.scalar_one() == 0:
                await conn.execute(
                    text(
                        """
                        INSERT INTO patient_profiles (id, user_id, full_name, date_of_birth, gender, emergency_contact, created_at, updated_at)
                        VALUES (gen_random_uuid(), :user_id, :full_name, :dob, :gender, :emergency, NOW(), NOW())
                        """
                    ),
                    {
                        "user_id": patient_id,
                        "full_name": "Test Patient",
                        "dob": date(1990, 1, 1),
                        "gender": "male",
                        "emergency": "+2348000000006",
                    },
                )
                print(f"  Created patient profile for patient@example.com")
    
    await engine.dispose()
    print("\nSeed completed successfully!")


if __name__ == "__main__":
    asyncio.run(seed())