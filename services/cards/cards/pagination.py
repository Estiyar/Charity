from rest_framework.pagination import LimitOffsetPagination, PageNumberPagination


class CatalogPagination(PageNumberPagination):
    page_size = 12
    page_size_query_param = "page_size"
    max_page_size = 50

    def paginate_queryset(self, queryset, request, view=None):
        if request.query_params.get("limit") is not None:
            self.offset_paginator = LimitOffsetPagination()
            self.offset_paginator.default_limit = self.page_size
            self.offset_paginator.max_limit = self.max_page_size
            return self.offset_paginator.paginate_queryset(queryset, request, view)
        self.offset_paginator = None
        return super().paginate_queryset(queryset, request, view)

    def get_paginated_response(self, data):
        if self.offset_paginator is not None:
            return self.offset_paginator.get_paginated_response(data)
        response = super().get_paginated_response(data)
        response.data["page"] = self.page.number
        response.data["page_size"] = self.get_page_size(self.request)
        return response
