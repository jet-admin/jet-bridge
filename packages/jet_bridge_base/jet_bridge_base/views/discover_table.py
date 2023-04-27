from sqlalchemy import MetaData, inspection
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.sql.base import _bind_or_error

from jet_bridge_base import settings
from jet_bridge_base.db import get_conf, get_connection_schema, get_connection_tunnel, create_connection_engine
from jet_bridge_base.exceptions.validation_error import ValidationError
from jet_bridge_base.permissions import HasProjectPermissions
from jet_bridge_base.reflect import get_tables
from jet_bridge_base.responses.json import JSONResponse
from jet_bridge_base.views.base.api import BaseAPIView


class DiscoverTableView(BaseAPIView):
    permission_classes = (HasProjectPermissions,)

    def required_project_permission(self, request):
        return {
            'permission_type': 'project',
            'permission_object': 'project_customization',
            'permission_actions': ''
        }

    def get(self, request, *args, **kwargs):
        conf = get_conf(request)
        schema = get_connection_schema(conf)

        tunnel = None
        bind = None

        try:
            tunnel = get_connection_tunnel(conf)
            bind = create_connection_engine(conf, tunnel)

            Session = scoped_session(sessionmaker(bind=bind))
            session = Session()

            with session.connection() as connection:
                metadata = MetaData(schema=schema, bind=connection)

                if bind is None:
                    bind = _bind_or_error(metadata)

                with inspection.inspect(bind)._inspection_context() as insp:
                    if schema is None:
                        schema = metadata.schema

                    load = get_tables(insp, metadata, bind, schema)

                    return JSONResponse({
                        'tables': load,
                        'max_tables': settings.DATABASE_MAX_TABLES
                    })
        except Exception as e:
            raise ValidationError(str(e))
        finally:
            if bind:
                bind.dispose()

            if tunnel:
                tunnel.close()
