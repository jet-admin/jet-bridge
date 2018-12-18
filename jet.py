import tornado.ioloop
import tornado.web
import adapters.postgres

from views.api import ApiHandler
from views.main import MainHandler
from views.model import ModelHandler
from views.model_description import ModelDescriptionsHandler
from views.register import RegisterHandler


def make_app():
    return tornado.web.Application([
        (r'/', MainHandler),
        (r'/register/', RegisterHandler),
        (r'/api/', ApiHandler),
        (r'/api/model_descriptions/', ModelDescriptionsHandler),
        (r'/api/models/(?P<model>[^/]+)/', ModelHandler),
    ], debug=True)

if __name__ == '__main__':
    app = make_app()
    app.listen(8888)
    tornado.ioloop.IOLoop.current().start()
