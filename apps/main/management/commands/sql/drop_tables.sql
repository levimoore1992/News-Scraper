-- Drop tables in a given database.

DO $$ DECLARE r RECORD;
    BEGIN FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = current_schema())
        LOOP EXECUTE 'DROP TABLE ' || quote_ident(r.tablename) || ' CASCADE'; END LOOP;
    END
$$;

DROP FUNCTION IF EXISTS maintain_dms_replication_progress_queue;
