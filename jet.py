import tornado.ioloop
import tornado.web
import adapters.postgres
from router import Router

from views.api import ApiHandler
from views.main import MainHandler
from views.model import ModelHandler
from views.model_description import ModelDescriptionsHandler
from views.not_found import NotFoundHandler
from views.register import RegisterHandler
from views.sql import SqlHandler


def make_app():
    router = Router()

    router.register('/api/models/(?P<model>[^/]+)/', ModelHandler)

    return tornado.web.Application([
        (r'/', MainHandler),
        (r'/register/', RegisterHandler),
        (r'/api/', ApiHandler),
        (r'/api/model_descriptions/', ModelDescriptionsHandler),
        (r'/api/sql/', SqlHandler),
    ] + router.urls, debug=True, default_handler_class=NotFoundHandler)

if __name__ == '__main__':
    app = make_app()
    app.listen(8888)
    tornado.ioloop.IOLoop.current().start()
