
-- Create Roles
DO $$
BEGIN


   IF NOT EXISTS (SELECT * FROM pg_catalog.pg_roles WHERE rolname = 'web') THEN
      CREATE ROLE "web";
   END IF;



END
$$;


-- Create Extensions
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
CREATE EXTENSION IF NOT EXISTS "pg_buffercache";

