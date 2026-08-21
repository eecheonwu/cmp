-- CMP Database Initialization Script
-- This script runs on PostgreSQL container startup

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create initial schema (tables will be managed by Alembic)
-- This is just for any initial setup needed

-- Create a test branch for development
-- Note: This is handled by Alembic migrations, but we can add seed data here if needed

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE cmp_db TO cmp_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO cmp_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO cmp_user;