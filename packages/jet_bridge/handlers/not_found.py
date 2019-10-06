import tornado.web


class NotFoundHandler(tornado.web.RequestHandler):

    def get(self, *args, **kwargs):
        self.set_status(404)
        self.render('404.html', **{
            'path': self.request.path,
        })
