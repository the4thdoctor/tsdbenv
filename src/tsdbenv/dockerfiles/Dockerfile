# Author: Wagner Bianchi <wagnerbianchijr@gmail.com>
# Created: 2026-08-19
# Dockerfile for PostgreSQL + TimescaleDB environment

ARG PG_VERSION=14

FROM postgres:${PG_VERSION}-alpine

# Install PostgreSQL contrib modules with TimescaleDB extension support
RUN apk add --no-cache postgresql-contrib timescaledb-postgresql-14 && \
    echo "shared_preload_libraries = 'timescaledb'" >> /usr/local/share/postgresql/postgresql.conf.sample

# Set environment variables for postgres user
ENV POSTGRES_USER=postgres
ENV POSTGRES_HOST_AUTH_METHOD=trust

# Expose PostgreSQL port
EXPOSE 5432

# Health check to verify PostgreSQL readiness
HEALTHCHECK --interval=10s --timeout=5s --retries=5 \
    CMD psql -U postgres -c "SELECT 1" || exit 1

# Copy initialization script to docker-entrypoint-initdb.d/
# This script executes automatically when PostgreSQL starts for the first time
COPY init-tsdbadmin.sql /docker-entrypoint-initdb.d/01-init-tsdbadmin.sql
