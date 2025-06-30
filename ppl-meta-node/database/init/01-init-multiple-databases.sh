#!/bin/bash
# Database initialization script for PPL Meta Platform
# Creates multiple databases for different microservices

set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- Create databases for different microservices
    CREATE DATABASE ppl_media_db;
    CREATE DATABASE ppl_orchestrator_db;
    
    -- Grant privileges
    GRANT ALL PRIVILEGES ON DATABASE ppl_db TO nickadmin;
    GRANT ALL PRIVILEGES ON DATABASE ppl_media_db TO nickadmin;
    GRANT ALL PRIVILEGES ON DATABASE ppl_orchestrator_db TO nickadmin;
    
    -- Create extensions if needed
    \c ppl_db
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
    
    \c ppl_media_db
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
    
    \c ppl_orchestrator_db
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
EOSQL
