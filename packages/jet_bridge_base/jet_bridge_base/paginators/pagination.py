
class Pagination(object):
    count = None

    def paginate_queryset(self, request, queryset, handler):
        raise NotImplementedError

    def get_paginated_response(self, request, data):
        raise NotImplementedError
