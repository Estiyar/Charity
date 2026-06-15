import django_filters

from .models import FundraisingCard


class CardFilter(django_filters.FilterSet):
    city = django_filters.CharFilter(lookup_expr="icontains")
    diagnosis = django_filters.CharFilter(lookup_expr="icontains")
    status = django_filters.CharFilter()
    end_date_from = django_filters.DateFilter(field_name="end_date", lookup_expr="gte")
    end_date_to = django_filters.DateFilter(field_name="end_date", lookup_expr="lte")
    target_amount_min = django_filters.NumberFilter(
        field_name="target_amount",
        lookup_expr="gte",
    )
    target_amount_max = django_filters.NumberFilter(
        field_name="target_amount",
        lookup_expr="lte",
    )

    class Meta:
        model = FundraisingCard
        fields = (
            "city",
            "diagnosis",
            "status",
            "end_date_from",
            "end_date_to",
            "target_amount_min",
            "target_amount_max",
        )
