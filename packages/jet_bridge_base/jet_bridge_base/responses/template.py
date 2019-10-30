from jet_bridge_base.responses.base import Response


class TemplateResponse(Response):

    def __init__(self, template, data=None, status=None, headers=None, exception=False, content_type=None):
        self.template = template
        super(TemplateResponse, self).__init__(data, status, headers, exception, content_type)
