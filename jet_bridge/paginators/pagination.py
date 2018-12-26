
class Pagination(object):
    count = None

    def paginate_queryset(self, queryset, handler):
        raise NotImplementedError

    def get_paginated_response(self, data):
        raise NotImplementedError
