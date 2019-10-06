import os

import tornado.ioloop
import tornado.web

from jet_bridge_base import media, settings as base_settings
from jet_bridge_base.views.api import ApiView
from jet_bridge_base.views.image_resize import ImageResizeView
from jet_bridge_base.views.media_file_upload import MediaFileUploadView
from jet_bridge_base.views.main import MainView
from jet_bridge_base.views.message import MessageView
from jet_bridge_base.views.model import ModelView
from jet_bridge_base.views.model_description import ModelDescriptionsView
from jet_bridge_base.views.register import RegisterView
from jet_bridge_base.views.sql import SqlView

from jet_bridge import settings
from jet_bridge.handlers.view import view_handler
from jet_bridge.handlers.not_found import NotFoundHandler
from jet_bridge.router import Router


def make_app():
    router = Router()

    router.register('/api/models/(?P<model>[^/]+)/', view_handler(ModelView))

    urls = [
        (r'/', view_handler(MainView)),
        (r'/register/', view_handler(RegisterView)),
        (r'/api/', view_handler(ApiView)),
        (r'/api/register/', view_handler(RegisterView)),
        (r'/api/model_descriptions/', view_handler(ModelDescriptionsView)),
        (r'/api/sql/', view_handler(SqlView)),
        (r'/api/messages/', view_handler(MessageView)),
        (r'/api/file_upload/', view_handler(MediaFileUploadView)),
        (r'/api/image_resize/', view_handler(ImageResizeView)),
        (r'/media/(.*)', tornado.web.StaticFileHandler, {'path': settings.MEDIA_ROOT}),
    ]
    urls += router.urls

    if settings.MEDIA_STORAGE == media.MEDIA_STORAGE_DEFAULT:
        urls.append((r'/media/(.*)', tornado.web.StaticFileHandler, {'path': settings.MEDIA_ROOT}))

    return tornado.web.Application(
        handlers=urls,
        debug=settings.DEBUG,
        default_handler_class=NotFoundHandler,
        template_path=os.path.join(base_settings.BASE_DIR, 'templates')
    )
