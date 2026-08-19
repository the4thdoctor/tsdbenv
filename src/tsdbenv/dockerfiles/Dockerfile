# Author: Wagner Bianchi <wagnerbianchijr@gmail.com>
# Created: 2026-08-19
# Dockerfile for PostgreSQL + TimescaleDB environment with Tiger Cloud extensions

ARG PG_VERSION=14

FROM timescale/timescaledb:latest-pg${PG_VERSION}-oss

# Install additional PostgreSQL extensions
RUN apt-get update && apt-get install -y \
    postgresql-${PG_VERSION}-pgvector \
    postgresql-${PG_VERSION}-postgres-fdw \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# TimescaleDB extension is pre-configured in the base image
# Add vector and other extensions to shared_preload_libraries
RUN echo "shared_preload_libraries = 'timescaledb,vector'" >> /etc/postgresql/postgresql.conf.sample

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
