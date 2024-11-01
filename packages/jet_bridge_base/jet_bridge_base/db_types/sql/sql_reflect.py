import time

from sqlalchemy.sql.base import _bind_or_error
from sqlalchemy import Table
from sqlalchemy import exc
from sqlalchemy import inspection
from sqlalchemy import util

from jet_bridge_base import settings
from jet_bridge_base.logger import logger
from jet_bridge_base.utils.process import get_memory_usage_human


def sql_get_tables(
    insp,
    metadata,
    bind=None,
    schema=None,
    foreign=False,
    views=False,
    only=None,
    extend_existing=False
):
    view_names = []

    available = util.OrderedSet(insp.get_table_names(schema))

    if foreign and hasattr(insp, 'get_foreign_table_names'):
        table_names = insp.get_foreign_table_names()
        available.update(table_names)

    if views:
        try:
            view_names = insp.get_view_names(schema)
            available.update(view_names)
        except NotImplementedError:
            pass

    if schema is not None:
        available_w_schema = util.OrderedSet(
            ["%s.%s" % (schema, name) for name in available]
        )
    else:
        available_w_schema = available

    current = set(metadata.tables)

    if only is None:
        load = [
            name
            for name, schname in zip(available, available_w_schema)
            if extend_existing or schname not in current
        ]
    elif callable(only):
        load = [
            name
            for name, schname in zip(available, available_w_schema)
            if (extend_existing or schname not in current) and only(name)
        ]
    else:
        missing = [name for name in only if name not in available]
        if missing:
            s = schema and (" schema '%s'" % schema) or ""
            raise exc.InvalidRequestError(
                "Could not reflect: requested table(s) not available "
                "in %r%s: (%s)" % (bind.engine, s, ", ".join(missing))
            )
        load = [
            name
            for name in only
            if extend_existing or name not in current
        ]

    return load, view_names


def sql_reflect(
    cid_short,
    metadata,
    bind=None,
    schema=None,
    foreign=False,
    views=False,
    only=None,
    extend_existing=False,
    autoload_replace=True,
    resolve_fks=True,
    pending_connection=None,
    **dialect_kwargs
):
    if bind is None:
        bind = _bind_or_error(metadata)

    with inspection.inspect(bind)._inspection_context() as insp:
        reflect_opts = {
            "autoload_with": insp,
            "extend_existing": extend_existing,
            "autoload_replace": autoload_replace,
            "resolve_fks": resolve_fks,
            "_extend_on": set(),
        }

        reflect_opts.update(dialect_kwargs)

        if schema is None:
            schema = metadata.schema

        if schema is not None:
            reflect_opts["schema"] = schema

        load, view_names = sql_get_tables(insp, metadata, bind, schema, foreign, views, only, extend_existing)

        """
        Modified: Added default PK set and progress display
        """

        if pending_connection:
            pending_connection['tables_total'] = len(load)

        i = 0
        for name in load:
            if name in ['pg_stat_statements']:
                continue

            # Wait to allow other threads execution
            time.sleep(0.01)

            try:
                logger.info('[{}] Analyzing table "{}" ({} / {})" (Mem:{})...'.format(cid_short, name, i + 1, len(load), get_memory_usage_human()))
                table = Table(name, metadata, **reflect_opts)

                if bind.engine.name == 'clickhouse':
                    table = metadata.tables[table.key]

                if view_names and name in view_names:
                    setattr(table, '__jet_is_view__', True)

                args = []
                has_pk = False
                first_column = None

                for item in table.columns:
                    if not has_pk and item.primary_key:
                        has_pk = True
                    if first_column is None:
                        first_column = item

                if not has_pk and first_column is not None:
                    logger.warning('[{}] Table "{}" is missing PK: "{}" column was set as PK'.format(cid_short, name, first_column.name))

                    first_column.primary_key = True
                    args.append(first_column)
                    reflect_opts['extend_existing'] = True
                    table = Table(name, metadata, *args, **reflect_opts)
                    setattr(table, '__jet_auto_pk__', True)


            except exc.UnreflectableTableError as uerr:
                util.warn("Skipping table %s: %s" % (name, uerr))

            i += 1

            if settings.DATABASE_MAX_TABLES is not None and i >= settings.DATABASE_MAX_TABLES:
                logger.warning('[{}] Max tables limit ({}) reached'.format(cid_short, settings.DATABASE_MAX_TABLES))
                break

            if pending_connection:
                pending_connection['tables_processed'] = i

    """
    Modify END
    """
