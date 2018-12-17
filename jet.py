import tornado.ioloop
import tornado.web
import adapters.postgres

from views.api import ApiHandler
from views.main import MainHandler
from views.model_description import ModelDescriptionsHandler


def make_app():
    return tornado.web.Application([
        (r'/', MainHandler),
        (r'/api/', ApiHandler),
        (r'/api/model_descriptions/', ModelDescriptionsHandler),
    ], debug=True)

if __name__ == '__main__':
    app = make_app()
    app.listen(8888)
    tornado.ioloop.IOLoop.current().start()
