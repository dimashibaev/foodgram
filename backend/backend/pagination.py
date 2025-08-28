from rest_framework.pagination import PageNumberPagination

from backend.const import MAX_PAGE_SIZE_PAGINATION, PAGE_SIZE_PAGINATION


class CustomPageNumberPagination(PageNumberPagination):
    page_size = PAGE_SIZE_PAGINATION
    page_size_query_param = 'limit'
    max_page_size = MAX_PAGE_SIZE_PAGINATION
