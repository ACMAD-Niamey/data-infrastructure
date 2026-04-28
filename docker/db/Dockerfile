FROM kartoza/postgis:18-3.6

USER root

RUN apt-get update \
    && apt-get install -y wget gnupg lsb-release ca-certificates \
    && mkdir -p /etc/apt/keyrings \
    && wget -qO- https://packagecloud.io/timescale/timescaledb/gpgkey \
       | gpg --dearmor -o /etc/apt/keyrings/timescaledb.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/timescaledb.gpg] https://packagecloud.io/timescale/timescaledb/debian/ $(. /etc/os-release && echo $VERSION_CODENAME) main" \
       > /etc/apt/sources.list.d/timescaledb.list \
    && apt-get update \
    && apt-get install -y timescaledb-2-postgresql-18 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*