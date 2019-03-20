FROM python:3.7.2-alpine

RUN \
 apk add --no-cache postgresql-libs mariadb-dev jpeg-dev zlib-dev && \
 apk add --no-cache --virtual .build-deps gcc musl-dev postgresql-dev

RUN addgroup -S jet && adduser -S -G jet jet
RUN pip install psycopg2 mysqlclient
RUN pip install jet_bridge==0.1.7
RUN apk --purge del .build-deps

USER jet

CMD ["jet_bridge"]

EXPOSE 8888
