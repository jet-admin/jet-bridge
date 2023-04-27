from sqlalchemy.orm import scoped_session, sessionmaker

from jet_bridge_base.db import get_conf, get_connection_tunnel, create_connection_engine
from jet_bridge_base.exceptions.validation_error import ValidationError
from jet_bridge_base.permissions import HasProjectPermissions
from jet_bridge_base.responses.json import JSONResponse
from jet_bridge_base.views.base.api import BaseAPIView


class DiscoverConnectionView(BaseAPIView):
    permission_classes = (HasProjectPermissions,)

    def required_project_permission(self, request):
        return {
            'permission_type': 'project',
            'permission_object': 'project_customization',
            'permission_actions': ''
        }

    def get(self, request, *args, **kwargs):
        conf = get_conf(request)

        tunnel = None
        bind = None

        try:
            tunnel = get_connection_tunnel(conf)
            bind = create_connection_engine(conf, tunnel)

            Session = scoped_session(sessionmaker(bind=bind))
            session = Session()

            with session.connection():
                return JSONResponse({
                    'status': True
                })
        except Exception as e:
            raise ValidationError(str(e))
        finally:
            if bind:
                bind.dispose()

            if tunnel:
                tunnel.close()
