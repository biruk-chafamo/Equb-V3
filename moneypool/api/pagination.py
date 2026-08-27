from rest_framework.pagination import PageNumberPagination


class BoundedPagination(PageNumberPagination):
    """A ceiling for collections that grow without limit."""

    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 200
