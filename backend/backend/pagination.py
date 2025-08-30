from rest_framework.pagination import PageNumberPagination

from backend.const import DEFAULT_PAGE_SIZE, MAX_DEFAULT_PAGE_SIZE


class CustomPageNumberPagination(PageNumberPagination):
    page_size = DEFAULT_PAGE_SIZE
    page_size_query_param = 'limit'
    max_page_size = MAX_DEFAULT_PAGE_SIZE
