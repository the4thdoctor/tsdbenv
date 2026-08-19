-- Author: Wagner Bianchi <wagnerbianchijr@gmail.com>
-- Created: 2026-08-19
-- Initialize tsdbadmin user and configuration

-- Create tsdbadmin user as superuser (same as postgres)
CREATE ROLE tsdbadmin WITH LOGIN SUPERUSER CREATEDB CREATEROLE PASSWORD :password;
-- Set default search_path for tsdbadmin
ALTER ROLE tsdbadmin SET search_path = public, pg_catalog;
