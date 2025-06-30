-- Initialize multiple databases for microservices
CREATE DATABASE IF NOT EXISTS ppl_media_db;
CREATE DATABASE IF NOT EXISTS user_management_db;

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE ppl_media_db TO nickadmin;
GRANT ALL PRIVILEGES ON DATABASE user_management_db TO nickadmin;
