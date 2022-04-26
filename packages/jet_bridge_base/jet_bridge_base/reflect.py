from sqlalchemy.sql.base import _bind_or_error
from sqlalchemy import Table
from sqlalchemy import exc
from sqlalchemy import inspection
from sqlalchemy import util

from jet_bridge_base.logger import logger


def reflect(
    metadata,
    bind=None,
    schema=None,
    views=False,
    only=None,
    extend_existing=False,
    autoload_replace=True,
    resolve_fks=True,
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

        available = util.OrderedSet(insp.get_table_names(schema))
        if views:
            available.update(insp.get_view_names(schema))

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
                if (extend_existing or schname not in current)
                   and only(name, metadata)
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

        """
        Modified: Added default PK set and progress display
        """

        i = 0
        for name in load:
            try:
                logger.info('Analyzing table "{}" ({} / {})"...'.format(name, i + 1, len(load)))
                table = Table(name, metadata, **reflect_opts)

                args = []
                has_pk = False
                first_column = None

                for item in table.columns:
                    if not has_pk and item.primary_key:
                        has_pk = True
                    if first_column is None:
                        first_column = item

                if not has_pk and first_column is not None:
                    logger.warning('Table "{}" is missing PK: "{}" column was set as PK'.format(name, first_column.name))

                    first_column.primary_key = True
                    args.append(first_column)
                    reflect_opts['extend_existing'] = True
                    Table(name, metadata, *args, **reflect_opts)


            except exc.UnreflectableTableError as uerr:
                util.warn("Skipping table %s: %s" % (name, uerr))

            i += 1

    """
    Modify END
    """
