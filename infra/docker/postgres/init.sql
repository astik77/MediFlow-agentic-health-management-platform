-- ============================================================
-- MEDIFLOW — PostgreSQL Initialization Script
-- Runs once on first container startup
-- ============================================================

-- Enable pgvector extension (required for embeddings in Phase 7)
CREATE EXTENSION IF NOT EXISTS vector;

-- Enable uuid-ossp for UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable pgcrypto for cryptographic functions
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Set search path
SET search_path TO public;

-- Confirm initialization
DO $$
BEGIN
  RAISE NOTICE 'MediFlow database initialized with extensions: vector, uuid-ossp, pgcrypto';
END $$;
