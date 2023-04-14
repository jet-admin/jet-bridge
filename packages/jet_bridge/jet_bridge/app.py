import os

import tornado.ioloop
import tornado.web

from jet_bridge.handlers.temporary_redirect import TemporaryRedirectHandler
from jet_bridge_base.sentry import sentry_controller
from jet_bridge_base.utils.async_exec import set_max_workers
from jet_bridge_base import settings as base_settings
from jet_bridge_base.views.api import ApiView
from jet_bridge_base.views.discover_connection import DiscoverConnectionView
from jet_bridge_base.views.discover_table import DiscoverTableView
from jet_bridge_base.views.external_auth.complete import ExternalAuthCompleteView
from jet_bridge_base.views.external_auth.login import ExternalAuthLoginView
from jet_bridge_base.views.graphql import GraphQLView
from jet_bridge_base.views.image_resize import ImageResizeView
from jet_bridge_base.views.file_upload import FileUploadView
from jet_bridge_base.views.message import MessageView
from jet_bridge_base.views.model import ModelViewSet
from jet_bridge_base.views.model_description import ModelDescriptionView
from jet_bridge_base.views.model_description_relationship_override import ModelDescriptionRelationshipOverrideView
from jet_bridge_base.views.proxy_request import ProxyRequestView
from jet_bridge_base.views.register import RegisterView
from jet_bridge_base.views.reload import ReloadView
from jet_bridge_base.views.sql import SqlView
from jet_bridge_base.views.status import StatusView
from jet_bridge_base.views.table import TableView
from jet_bridge_base.views.table_column import TableColumnView

from jet_bridge import settings, media, VERSION
from jet_bridge.handlers.view import view_handler
from jet_bridge.handlers.not_found import NotFoundHandler
from jet_bridge.router import Router
from jet_bridge_base.views.trigger_exception import TriggerExceptionView


def make_app():
    router = Router()

    router.register('/api/models/(?P<model>[^/]+)/', view_handler(ModelViewSet))
    router.register('/api/tables/(?P<table>[^/]+)/columns/', view_handler(TableColumnView))
    router.register('/api/tables/', view_handler(TableView))

    urls = [
        (r'/', TemporaryRedirectHandler, {'url': '/api/'}),
        (r'/register/', view_handler(RegisterView)),
        (r'/api/', view_handler(ApiView)),
        (r'/api/register/', view_handler(RegisterView)),
        (r'/api/graphql/', view_handler(GraphQLView)),
        (r'/api/model_descriptions/relationship_overrides/', view_handler(ModelDescriptionRelationshipOverrideView)),
        (r'/api/model_descriptions/', view_handler(ModelDescriptionView)),
        (r'/api/sql/', view_handler(SqlView)),
        (r'/api/messages/', view_handler(MessageView)),
        (r'/api/file_upload/', view_handler(FileUploadView)),
        (r'/api/image_resize/', view_handler(ImageResizeView)),
        (r'/api/reload/', view_handler(ReloadView)),
        (r'/api/proxy_request/', view_handler(ProxyRequestView)),
        (r'/api/discover/connection/', view_handler(DiscoverConnectionView)),
        (r'/api/discover/tables/', view_handler(DiscoverTableView)),
        (r'/media/(.*)', tornado.web.StaticFileHandler, {'path': settings.MEDIA_ROOT}),
        (r'/api/external_auth/login/(?P<app>[^/]+)/', view_handler(ExternalAuthLoginView)),
        (r'/api/external_auth/complete/(?P<app>[^/]+)/', view_handler(ExternalAuthCompleteView)),
        (r'/api/status/', view_handler(StatusView)),
        (r'/api/trigger_exception/', view_handler(TriggerExceptionView)),
    ]
    urls += router.urls

    if settings.MEDIA_STORAGE == media.MEDIA_STORAGE_FILE:
        urls.append((r'/media/(.*)', tornado.web.StaticFileHandler, {'path': settings.MEDIA_ROOT}))

    if settings.THREADS is not None:
        set_max_workers(settings.THREADS)

    if settings.SENTRY_DSN:
        sentry_controller.enable(
            dsn=settings.SENTRY_DSN,
            release='jet-bridge@{}'.format(VERSION),
            tornado=True
        )

    return tornado.web.Application(
        handlers=urls,
        debug=settings.DEBUG,
        default_handler_class=NotFoundHandler,
        template_path=os.path.join(base_settings.BASE_DIR, 'templates'),
        autoreload=settings.DEBUG,
        cookie_secret=settings.TOKEN
    )
