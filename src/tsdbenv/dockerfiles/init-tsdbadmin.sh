#!/bin/bash
# Author: Wagner Bianchi <wagnerbianchijr@gmail.com>
# Created: 2026-08-19
# Wrapper script to initialize tsdbadmin user with password from environment variable

set -e

# Get password from environment variable (defaults to empty if not set)
PASSWORD="${TSDBADMIN_PASSWORD:-}"

# Execute init-tsdbadmin.sql with password variable passed via psql -v flag
psql -v password="$PASSWORD" <<'EOF'
-- Create tsdbadmin user as superuser (same as postgres)
CREATE ROLE tsdbadmin WITH LOGIN SUPERUSER CREATEDB CREATEROLE PASSWORD :'password';
-- Set default search_path for tsdbadmin
ALTER ROLE tsdbadmin SET search_path = public, pg_catalog;
EOF
