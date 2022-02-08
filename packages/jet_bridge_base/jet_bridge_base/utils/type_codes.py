import re

from jet_bridge_base.utils.queryset import get_session_engine


def fetch_postgresql_type_code_to_sql_type(session):
    from sqlalchemy.dialects.postgresql.base import ischema_names

    result = {}
    types_cursor = session.execute('''
        SELECT 
            pg_catalog.format_type(oid, NULL),
            oid 
        FROM 
            pg_type
    ''')
    for pg_type in types_cursor:
        # Copied from:
        # def _get_column_info
        # site-packages/sqlalchemy/dialects/postgresql/base.py:3716

        type_code = pg_type['oid']
        format_type = pg_type['format_type']

        def _handle_array_type(attype):
            return (
                # strip '[]' from integer[], etc.
                re.sub(r"\[\]$", "", attype),
                attype.endswith("[]"),
            )

        # strip (*) from character varying(5), timestamp(5)
        # with time zone, geometry(POLYGON), etc.
        attype = re.sub(r"\(.*\)", "", format_type)

        # strip '[]' from integer[], etc. and check if an array
        attype, is_array = _handle_array_type(attype)

        if attype.startswith('interval'):
            attype = 'interval'

        sql_type = ischema_names.get(attype)

        if sql_type:
            result[type_code] = sql_type

    return result


def fetch_type_code_to_sql_type(session):
    if get_session_engine(session) == 'postgresql':
        return fetch_postgresql_type_code_to_sql_type(session)
