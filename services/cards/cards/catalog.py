import hashlib
import json
from decimal import Decimal, InvalidOperation

from django.db.models import Case, DecimalField, ExpressionWrapper, F, Q, Value, When

from ekomek_common.constants import PUBLIC_CARD_STATUSES

from .catalog_cache import catalog_cache_get, catalog_cache_set, catalog_version
from .models import FundraisingCard


def parse_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def parse_decimal(value):
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


ALLOWED_ORDERING = {
    "target_amount",
    "collected_amount",
    "age",
    "end_date",
    "created_at",
    "progress",
}

DECIMAL = DecimalField(max_digits=18, decimal_places=4)


def progress_annotation():
    ratio = ExpressionWrapper(
        F("collected_amount") * Value(Decimal("100")) / F("target_amount"),
        output_field=DECIMAL,
    )
    return Case(
        When(target_amount=0, then=Value(Decimal("0"))),
        default=ratio,
        output_field=DECIMAL,
    )


def public_catalog_queryset():
    return FundraisingCard.objects.filter(status__in=PUBLIC_CARD_STATUSES)


def apply_catalog_filters(queryset, params):
    city = (params.get("city") or "").strip()
    diagnosis = (params.get("diagnosis") or "").strip()
    status_value = (params.get("status") or "").strip()
    search = (params.get("search") or "").strip()
    if city:
        queryset = queryset.filter(city__icontains=city)
    if diagnosis:
        queryset = queryset.filter(diagnosis__icontains=diagnosis)
    if status_value:
        if status_value not in PUBLIC_CARD_STATUSES:
            return queryset.none()
        queryset = queryset.filter(status=status_value)
    amount_min = parse_decimal(params.get("target_amount_min"))
    amount_max = parse_decimal(params.get("target_amount_max"))
    if amount_min is not None:
        queryset = queryset.filter(target_amount__gte=amount_min)
    if amount_max is not None:
        queryset = queryset.filter(target_amount__lte=amount_max)
    age_min = parse_int(params.get("age_min"))
    age_max = parse_int(params.get("age_max"))
    if age_min is not None:
        queryset = queryset.filter(age__gte=age_min)
    if age_max is not None:
        queryset = queryset.filter(age__lte=age_max)
    end_from = (params.get("end_date_from") or "").strip()
    end_to = (params.get("end_date_to") or "").strip()
    if end_from:
        queryset = queryset.filter(end_date__gte=end_from)
    if end_to:
        queryset = queryset.filter(end_date__lte=end_to)
    if search:
        queryset = queryset.filter(
            Q(full_name__icontains=search)
            | Q(diagnosis__icontains=search)
            | Q(city__icontains=search)
            | Q(description__icontains=search)
        )
    return queryset


def apply_catalog_ordering(queryset, ordering):
    raw = (ordering or "-created_at").strip()
    descending = raw.startswith("-")
    field = raw.lstrip("-")
    if field not in ALLOWED_ORDERING:
        return queryset.order_by("-created_at", "-id")
    prefix = "-" if descending else ""
    if field == "progress":
        return queryset.annotate(progress=progress_annotation()).order_by(f"{prefix}progress", "-id")
    return queryset.order_by(f"{prefix}{field}", "-id")


def filtered_catalog_queryset(params):
    queryset = apply_catalog_filters(public_catalog_queryset(), params)
    return apply_catalog_ordering(queryset, params.get("ordering"))


def catalog_query_cache_key(params):
    canonical = json.dumps(sorted((params or {}).items()), ensure_ascii=True, default=str)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24]
    return f"catalog:v{catalog_version()}:{digest}"


def cached_catalog_payload(params, builder):
    key = catalog_query_cache_key(params)
    cached = catalog_cache_get(key)
    if cached is not None:
        return cached, True
    payload = builder()
    catalog_cache_set(key, payload)
    return payload, False


def catalog_references():
    key = f"catalog:refs:v{catalog_version()}"
    cached = catalog_cache_get(key)
    if cached is not None:
        return cached
    public = public_catalog_queryset()
    payload = {
        "cities": list(
            public.exclude(city="").order_by("city").values_list("city", flat=True).distinct()
        ),
        "diagnoses": list(
            public.exclude(diagnosis="").order_by("diagnosis").values_list("diagnosis", flat=True).distinct()
        ),
    }
    catalog_cache_set(key, payload)
    return payload
