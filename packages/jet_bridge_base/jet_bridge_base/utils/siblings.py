from sqlalchemy import inspect, func
from sqlalchemy.orm import load_only

from jet_bridge_base.utils.queryset import apply_default_ordering, queryset_count_optimized


def get_row_number(Model, queryset, instance):
    mapper = inspect(Model)
    pk = mapper.primary_key[0].name

    subqquery = queryset.with_entities(
        mapper.primary_key[0].label('__inner__pk'),
        func.row_number().over(order_by=queryset._order_by).label('__inner__row')
    ).subquery()

    rest = queryset.session.query(subqquery.c.__inner__row).filter(subqquery.c.__inner__pk == getattr(instance, pk))
    return rest.scalar()


def get_row_siblings(Model, queryset, row_number):
    mapper = inspect(Model)
    pk = mapper.primary_key[0].name

    has_prev = row_number > 1
    offset = row_number - 2 if has_prev else row_number - 1
    limit = 3 if has_prev else 2

    rows = queryset.options(load_only(pk)).limit(limit).offset(offset).all()

    if has_prev:
        next_index = 2
    else:
        next_index = 1

    if next_index >= len(rows):
        next_index = None

    if has_prev:
        prev_index = 0
    else:
        prev_index = None

    def map_row(row):
        return dict(((pk, getattr(row, pk)),))

    return {
        'prev': map_row(rows[prev_index]) if prev_index is not None else None,
        'next': map_row(rows[next_index]) if next_index is not None else None
    }


def get_model_siblings(request, Model, instance, queryset):
    count = queryset_count_optimized(request, queryset)

    if count > 10000:
        return {}

    queryset = apply_default_ordering(queryset)
    row_number = get_row_number(Model, queryset, instance)

    if not row_number:
        return {}

    return get_row_siblings(Model, queryset, row_number)
