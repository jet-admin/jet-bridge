from sqlalchemy import inspect, desc, func
from sqlalchemy.orm import load_only
from sqlalchemy.sql import operators
from sqlalchemy.sql.elements import AnnotatedColumnElement, UnaryExpression


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


def get_model_siblings(Model, instance, queryset):
    mapper = inspect(Model)
    pk = mapper.primary_key[0].name
    context = queryset._compile_context()
    ordering = context.order_by

    def is_pk(x):
        if isinstance(x, AnnotatedColumnElement):
            return x.name == pk
        elif isinstance(x, UnaryExpression):
            return x.element.name == pk and x.modifier == operators.desc_op
        return False

    if ordering is None or not any(map(is_pk, ordering)):
        order_by = list(ordering or []) + [desc(pk)]
        queryset = queryset.order_by(*order_by)

    row_number = get_row_number(Model, queryset, instance)

    if not row_number:
        return {}

    return get_row_siblings(Model, queryset, row_number)
