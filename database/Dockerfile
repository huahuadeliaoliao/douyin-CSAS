FROM postgres:16.4-bullseye

USER root
RUN mkdir -p /var/lib/pgsql/data && chown -R postgres:postgres /var/lib/pgsql

USER postgres
ENV PGDATA=/var/lib/pgsql/data

RUN pg_ctl initdb -D $PGDATA

COPY postgresql.conf /var/lib/pgsql/data/postgresql.conf
COPY pg_hba.conf     /var/lib/pgsql/data/pg_hba.conf

COPY init.sh /init.sh
RUN sh /init.sh

CMD ["postgres"]
