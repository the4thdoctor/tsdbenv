# Author: Wagner Bianchi <wagnerbianchijr@gmail.com>
# Created: 2026-08-19
# Dockerfile for PostgreSQL + TimescaleDB environment

ARG PG_VERSION=14

FROM timescale/timescaledb:latest-pg${PG_VERSION}-oss

# TimescaleDB extension is pre-configured in the base image
# Verify TimescaleDB is in shared_preload_libraries (already set by base image)

# Set environment variables for postgres user
ENV POSTGRES_USER=postgres

# Expose PostgreSQL port
EXPOSE 5432

# Health check to verify PostgreSQL readiness
HEALTHCHECK --interval=10s --timeout=5s --retries=5 \
    CMD psql -U postgres -c "SELECT 1" || exit 1

# Copy initialization script to docker-entrypoint-initdb.d/
# This script executes automatically when PostgreSQL starts for the first time
# Use wrapper script to handle password variable substitution
COPY init-tsdbadmin.sh /docker-entrypoint-initdb.d/01-init-tsdbadmin.sh
RUN chmod +x /docker-entrypoint-initdb.d/01-init-tsdbadmin.sh
