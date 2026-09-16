-- Remove empty duplicate "tapo corridor Collection" (id=1).
BEGIN;
DELETE FROM collection_storage_usage WHERE collection_id = 1;
DELETE FROM collection_storage_configs WHERE collection_id = 1;
DELETE FROM media_collection_items WHERE collection_id = 1;
DELETE FROM media_collections WHERE id = 1;
COMMIT;
