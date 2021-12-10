from sqlalchemy import inspect, desc
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import operators, text
from sqlalchemy.sql.elements import AnnotatedColumnElement, UnaryExpression

from jet_bridge_base import settings


def get_queryset_order_by(queryset):
    if hasattr(queryset, '_order_by_clauses') and queryset._order_by_clauses:
        return queryset._order_by_clauses
    elif hasattr(queryset, '_order_by') and queryset._order_by:
        return queryset._order_by
    else:
        return []


def get_queryset_limit(queryset):
    if hasattr(queryset, '_limit_clause') and queryset._limit_clause:
        return queryset._limit_clause
    elif hasattr(queryset, '_limit') and queryset._limit:
        return queryset._limit


def apply_default_ordering(Model, queryset):
    mapper = inspect(Model)
    pk = mapper.primary_key[0].name
    ordering = get_queryset_order_by(queryset)

    def is_pk(x):
        if isinstance(x, AnnotatedColumnElement):
            return x.name == pk
        elif isinstance(x, UnaryExpression):
            return hasattr(x.element, 'name') and x.element.name == pk and x.modifier == operators.desc_op
        return False

    if ordering is None or not any(map(is_pk, ordering)):
        queryset = queryset.order_by(desc(pk))

    return queryset


def queryset_count_optimized_for_postgresql(request, db_table):
    try:
        cursor = request.session.execute(text('SELECT reltuples FROM pg_class WHERE relname = :db_table'), {'db_table': db_table})
        row = cursor.fetchone()
        return int(row[0])
    except SQLAlchemyError:
        request.session.rollback()
        raise


def queryset_count_optimized_for_mysql(request, db_table):
    try:
        cursor = request.session.execute(text('EXPLAIN SELECT COUNT(*) FROM `{}`'.format(db_table)))
        row = cursor.fetchone()
        return int(row[8])
    except SQLAlchemyError:
        request.session.rollback()
        raise


def queryset_count_optimized(request, queryset):
    result = None
    table_size = None

    try:
        table = queryset.statement.froms[0].name

        if get_session_engine(queryset.session) == 'postgresql':
            table_size = queryset_count_optimized_for_postgresql(request, table)
        elif get_session_engine(queryset.session) == 'mysql':
            table_size = queryset_count_optimized_for_mysql(request, table)
    except:
        pass

    if queryset.whereclause is None and table_size is not None:
        result = table_size

    if table_size >= 10000:
        return result

    try:
        return queryset.count()
    except SQLAlchemyError:
        queryset.session.rollback()
        raise

def get_session_engine(session):
    return session.bind.engine.name
