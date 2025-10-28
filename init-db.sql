-- Initialize PostGIS extensions
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create spatial indexes for better performance
-- These will be created by SQLAlchemy, but we can add them here for reference
-- CREATE INDEX IF NOT EXISTS idx_users_location ON users USING GIST (location);
-- CREATE INDEX IF NOT EXISTS idx_users_id ON users (id);
-- CREATE INDEX IF NOT EXISTS idx_reviews_status ON reviews (status);
-- CREATE INDEX IF NOT EXISTS idx_reviews_reviewer ON reviews (reviewer_id);
