FROM python:3.7.6-alpine3.11

RUN apk add --no-cache \
    mariadb-dev>=10.4.15-r0 \
    jpeg-dev>=8-r6 \
    zlib-dev>=1.2.11-r3 \
    gcc>=9.3.0-r0 \
    g++>=9.3.0-r0 \
    musl-dev>=1.1.24-r3 \
    postgresql-dev>=12.5-r0 \
    postgresql-libs>=12.5-r0 \
    unixodbc-dev>=2.3.7-r2 \
    freetds-dev>=1.1.20-r0 \
    gdal-dev>=3.0.3-r0 \
    geos-dev>=3.8.0-r0 \
    proj-dev>=6.2.1-r0 \
    libffi-dev>=3.2.1-r6

#RUN addgroup -S jet && adduser -S -G jet jet
RUN pip install psycopg2==2.8.4 mysqlclient==1.4.6 pyodbc==4.0.30 GeoAlchemy2==0.6.2 Shapely==1.6.4 cryptography==3.3.1
RUN printf "[FreeTDS]\nDescription=FreeTDS Driver\nDriver=/usr/lib/libtdsodbc.so\n" > /etc/odbcinst.ini

COPY packages /packages
RUN pip install -e /packages/jet_bridge_base
RUN pip install -e /packages/jet_bridge

RUN mkdir /jet
VOLUME /jet
WORKDIR /jet

#USER jet

COPY docker/entrypoint.sh /
COPY docker/network-entrypoint.sh /
RUN chmod +x /entrypoint.sh
RUN chmod +x /network-entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
