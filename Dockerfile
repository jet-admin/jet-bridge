FROM python:3.7.2-alpine

RUN \
 apk add --no-cache postgresql-libs mariadb-dev jpeg-dev zlib-dev && \
 apk add --no-cache --virtual .build-deps gcc musl-dev postgresql-dev

RUN apk add --no-cache --virtual .build-deps-testing \
    --repository http://dl-cdn.alpinelinux.org/alpine/edge/main \
    --repository http://dl-cdn.alpinelinux.org/alpine/edge/testing \
    gdal-dev \
    geos-dev \
    proj4-dev

RUN addgroup -S jet && adduser -S -G jet jet
RUN pip install psycopg2 mysqlclient
RUN pip install GeoAlchemy2==0.6.2 Shapely==1.6.4
RUN pip install jet_bridge==0.2.6

USER jet

CMD ["jet_bridge"]

EXPOSE 8888
