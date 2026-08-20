import json

from django.core.serializers.json import DjangoJSONEncoder
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .catalog import catalog_references, cached_catalog_payload, filtered_catalog_queryset
from .pagination import CatalogPagination
from .serializers import CardPublicSerializer


def query_params_map(request):
    return {key: value for key, value in request.query_params.items() if value not in (None, "")}


def as_plain(data):
    return json.loads(json.dumps(data, cls=DjangoJSONEncoder))


class CatalogListView(APIView):
    permission_classes = [AllowAny]
    pagination_class = CatalogPagination

    def get(self, request):
        params = query_params_map(request)
        paginator = self.pagination_class()
        use_cache = not getattr(request.user, "is_authenticated", False)

        def build():
            queryset = filtered_catalog_queryset(params)
            page = paginator.paginate_queryset(queryset, request, view=self)
            cards = page if page is not None else queryset
            data = CardPublicSerializer(cards, many=True, context={"request": request}).data
            if page is not None:
                return as_plain(paginator.get_paginated_response(data).data)
            return as_plain({"count": len(data), "results": data})

        if use_cache:
            payload, _hit = cached_catalog_payload(params, build)
            return Response(payload)
        return Response(build())


class CatalogReferencesView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response(catalog_references())
