-- Initialize multiple databases for microservices
-- PostgreSQL syntax for creating databases
CREATE DATABASE ppl_media_db;
CREATE DATABASE user_management_db;

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE ppl_media_db TO nickadmin;
GRANT ALL PRIVILEGES ON DATABASE user_management_db TO nickadmin;
