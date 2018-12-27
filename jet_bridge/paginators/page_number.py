from collections import OrderedDict

import math
import tornado.web

from jet_bridge.paginators.pagination import Pagination
from jet_bridge.responses.base import Response
from jet_bridge.utils.http import replace_query_param, remove_query_param


class PageNumberPagination(Pagination):
    page_number = None
    page_size = 25
    page_query_param = 'page'
    page_size_query_param = '_per_page'
    max_page_size = 10000
    handler = None

    def paginate_queryset(self, queryset, handler):
        page_number = self.get_page_number(handler)
        if not page_number:
            return None

        page_size = self.get_page_size(handler)
        if not page_size:
            return None

        self.count = queryset.count()
        self.page_number = page_number
        self.page_size = page_size
        self.handler = handler

        queryset = queryset.offset((page_number - 1) * page_size).limit(page_size)

        return list(queryset)

    def get_pages_count(self):
        return int(math.ceil(self.count / self.page_size))

    def get_paginated_response(self, data):
        return Response(OrderedDict([
            ('count', self.count),
            ('next', self.get_next_link()),
            ('previous', self.get_previous_link()),
            ('results', data),
            ('num_pages', self.get_pages_count()),
            ('per_page', self.page_size),
        ]))

    def get_page_number(self, handler):
        try:
            result = int(handler.get_argument(self.page_query_param))
            return max(result, 1)
        except (tornado.web.MissingArgumentError, ValueError):
            return 1

    def get_page_size(self, handler):
        if self.page_size_query_param:
            try:
                result = int(handler.get_argument(self.page_size_query_param))
                result = max(result, 1)

                if self.max_page_size:
                    result = min(result, self.max_page_size)

                return result
            except (tornado.web.MissingArgumentError, ValueError):
                pass

        return self.page_size

    def has_next(self):
        return self.page_number < self.get_pages_count()

    def has_previous(self):
        return self.page_number > 1

    def next_page_number(self):
        return self.page_number + 1

    def previous_page_number(self):
        return self.page_number - 1

    def get_next_link(self):
        if not self.has_next():
            return None
        url = self.handler.request.full_url()
        page_number = self.next_page_number()
        return replace_query_param(url, self.page_query_param, page_number)

    def get_previous_link(self):
        if not self.has_previous():
            return None
        url = self.handler.request.full_url()
        page_number = self.previous_page_number()
        if page_number == 1:
            return remove_query_param(url, self.page_query_param)
        return replace_query_param(url, self.page_query_param, page_number)
