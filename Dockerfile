FROM jetadmin/jet-bridge-base:1.3.2

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
