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
-- Create default tsdb database owned by tsdbadmin
CREATE DATABASE tsdb OWNER tsdbadmin;
-- Set default search_path for tsdbadmin
ALTER ROLE tsdbadmin SET search_path = public, pg_catalog;
EOF

# Connect to tsdb and create extensions
psql -d tsdb -U postgres <<'EOF'
-- Create TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;
-- Create vector extension (pgvector)
CREATE EXTENSION IF NOT EXISTS vector;
-- Create postgres_fdw for remote connections
CREATE EXTENSION IF NOT EXISTS postgres_fdw;
-- Create pg_buffercache for buffer analysis
CREATE EXTENSION IF NOT EXISTS pg_buffercache;
-- Create pg_stat_statements for query statistics
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
-- Create TimescaleDB toolkit for advanced analytics
CREATE EXTENSION IF NOT EXISTS timescaledb_toolkit CASCADE;
EOF
