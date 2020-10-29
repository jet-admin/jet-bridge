from sqlalchemy import inspect, desc
from sqlalchemy.sql import operators, text
from sqlalchemy.sql.elements import AnnotatedColumnElement, UnaryExpression

from jet_bridge_base import settings
from jet_bridge_base.db import get_engine


def get_queryset_model(queryset):
    return queryset._primary_entity.entity_zero_or_selectable.entity


def apply_default_ordering(queryset):
    model = get_queryset_model(queryset)
    mapper = inspect(model)
    pk = mapper.primary_key[0].name
    ordering = queryset._order_by if queryset._order_by else []

    def is_pk(x):
        if isinstance(x, AnnotatedColumnElement):
            return x.name == pk
        elif isinstance(x, UnaryExpression):
            return x.element.name == pk and x.modifier == operators.desc_op
        return False

    if ordering is None or not any(map(is_pk, ordering)):
        order_by = list(ordering or []) + [desc(pk)]
        queryset = queryset.order_by(*order_by)

    return queryset


def queryset_count_optimized_for_postgresql(request, db_table):
    engine = get_engine(request)
    with engine.connect() as connection:
        cursor = connection.execute(text('SELECT reltuples FROM pg_class WHERE relname = :db_table'), {'db_table': db_table})
        row = cursor.fetchone()
        return int(row[0])


def queryset_count_optimized_for_mysql(request, db_table):
    engine = get_engine(request)
    with engine.connect() as connection:
        cursor = connection.execute(text('EXPLAIN SELECT COUNT(*) FROM `{}`'.format(db_table)))
        row = cursor.fetchone()
        return int(row[8])


def queryset_count_optimized(request, queryset):
    result = None

    if queryset.whereclause is None:
        try:
            table = queryset.statement.froms[0].name
            if settings.DATABASE_ENGINE == 'postgresql':
                result = queryset_count_optimized_for_postgresql(request, table)
            elif settings.DATABASE_ENGINE == 'mysql':
                result = queryset_count_optimized_for_mysql(request, table)
        except:
            pass

    if result is not None and result >= 10000:
        return result

    return queryset.count()
