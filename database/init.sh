#!/usr/bin/env sh
set -e
pg_ctl start -D $PGDATA
psql -c 'CREATE DATABASE database;'
