-- 006_grant_permissions.sql
-- Grants required table and routine privileges to service_role and authenticated users in Supabase

GRANT USAGE ON SCHEMA public TO anon, authenticated, service_role;

GRANT ALL ON ALL TABLES IN SCHEMA public TO service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO service_role;
GRANT ALL ON ALL ROUTINES IN SCHEMA public TO service_role;

-- Ensure analysis_runs has proper privileges
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.analysis_runs TO service_role;
