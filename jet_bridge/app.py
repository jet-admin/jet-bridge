import os

import tornado.ioloop
import tornado.web

from jet_bridge import settings, media
from jet_bridge.router import Router
from jet_bridge.views.api import ApiHandler
from jet_bridge.views.image_resize import ImageResizeHandler
from jet_bridge.views.media_file_upload import MediaFileUploadHandler
from jet_bridge.views.main import MainHandler
from jet_bridge.views.message import MessageHandler
from jet_bridge.views.model import ModelHandler
from jet_bridge.views.model_description import ModelDescriptionsHandler
from jet_bridge.views.not_found import NotFoundHandler
from jet_bridge.views.register import RegisterHandler
from jet_bridge.views.sql import SqlHandler


def make_app():
    router = Router()

    router.register('/api/models/(?P<model>[^/]+)/', ModelHandler)

    urls = [
        (r'/', MainHandler),
        (r'/register/', RegisterHandler),
        (r'/api/', ApiHandler),
        (r'/api/register/', RegisterHandler),
        (r'/api/model_descriptions/', ModelDescriptionsHandler),
        (r'/api/sql/', SqlHandler),
        (r'/api/messages/', MessageHandler),
        (r'/api/file_upload/', MediaFileUploadHandler),
        (r'/api/image_resize/', ImageResizeHandler),
        (r'/media/(.*)', tornado.web.StaticFileHandler, {'path': settings.MEDIA_ROOT}),
    ]
    urls += router.urls

    if settings.MEDIA_STORAGE == media.MEDIA_STORAGE_DEFAULT:
        urls.append((r'/media/(.*)', tornado.web.StaticFileHandler, {'path': settings.MEDIA_ROOT}))

    return tornado.web.Application(
        handlers=urls,
        debug=settings.DEBUG,
        default_handler_class=NotFoundHandler,
        template_path=os.path.join(settings.BASE_DIR, 'templates')
    )
