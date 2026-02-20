import time
from collections import OrderedDict
import math

from jet_bridge_base.db_types import queryset_count_optimized
from jet_bridge_base.exceptions.missing_argument_error import MissingArgumentError
from jet_bridge_base.paginators.pagination import Pagination
from jet_bridge_base.responses.json import JSONResponse
from jet_bridge_base.utils.http import replace_query_param, remove_query_param


class PageNumberPagination(Pagination):
    default_page_size = 25
    page_query_param = 'page'
    page_size_query_param = '_per_page'
    max_page_size = 10000

    count = None
    count_query_time = None
    page_number = None
    page_size = None
    data_query_time = None
    handler = None

    def paginate_queryset(self, request, queryset, handler):
        page_number = self.get_page_number(request, handler)
        if not page_number:
            return None

        page_size = self.get_page_size(request, handler)
        if not page_size:
            return None

        data_query_start = time.time()
        result = list(queryset.offset((page_number - 1) * page_size).limit(page_size))
        data_query_end = time.time()

        self.data_query_time = round(data_query_end - data_query_start, 3)

        count_query_start = time.time()
        if page_number == 1 and len(result) < page_size:
            self.count = len(result)
        else:
            self.count = queryset_count_optimized(request.session, queryset)
        count_query_end = time.time()

        self.count_query_time = round(count_query_end - count_query_start, 3)

        self.page_number = page_number
        self.page_size = page_size
        self.handler = handler

        return result

    def get_pages_count(self):
        return int(math.ceil(self.count / self.page_size)) if self.count is not None else None

    def get_paginated_response(self, request, data):
        return JSONResponse(OrderedDict([
            ('count', self.count),
            ('next', self.get_next_link(request, data)),
            ('previous', self.get_previous_link(request)),
            ('results', data),
            ('num_pages', self.get_pages_count()),
            ('per_page', self.page_size),
            ('has_more', self.has_next_potential(data)),
            ('data_query_time', self.data_query_time),
            ('count_query_time', self.count_query_time),
        ]))

    def get_page_number(self, request, handler):
        try:
            result = int(request.get_argument(self.page_query_param))
            return max(result, 1)
        except (MissingArgumentError, ValueError):
            return 1

    def get_page_size(self, request, handler):
        if self.page_size_query_param:
            try:
                result = int(request.get_argument(self.page_size_query_param))
                result = max(result, 1)

                if self.max_page_size:
                    result = min(result, self.max_page_size)

                return result
            except (MissingArgumentError, ValueError):
                pass

        return self.default_page_size

    def has_next(self):
        pages_count = self.get_pages_count()
        return self.page_number < pages_count if pages_count is not None else None

    def has_next_potential(self, data):
        has_next = self.has_next()
        if has_next is False and len(data) == self.page_size:
            # count may be inaccurate
            return True
        elif has_next is False:
            return has_next
        elif has_next is None and len(data) == 0:
            return False
        return True

    def has_previous(self):
        return self.page_number > 1

    def next_page_number(self):
        return self.page_number + 1

    def previous_page_number(self):
        return self.page_number - 1

    def get_next_link(self, request, data):
        if not self.has_next_potential(data):
            return None
        url = request.full_url()
        page_number = self.next_page_number()
        return replace_query_param(url, self.page_query_param, page_number)

    def get_previous_link(self, request):
        if not self.has_previous():
            return None
        url = request.full_url()
        page_number = self.previous_page_number()
        if page_number == 1:
            return remove_query_param(url, self.page_query_param)
        return replace_query_param(url, self.page_query_param, page_number)
