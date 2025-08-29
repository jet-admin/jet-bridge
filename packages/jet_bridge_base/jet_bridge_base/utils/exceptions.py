import re
import six

from jet_bridge_base.db_types import inspect_uniform
from jet_bridge_base.exceptions.validation_error import ValidationError
from jet_bridge_base.utils.common import force_array


def serialize_validation_error(exc):
    def map_error(value):
        return list(map(lambda x: str(x), force_array(value)))

    if isinstance(exc.detail, dict):
        return dict(map(lambda x: (x[0], map_error(x[1])), exc.detail.items()))
    elif isinstance(exc.detail, list):
        return {'non_field_errors': map_error(exc.detail)}
    else:
        return {'non_field_errors': [str(exc.detail)]}


def validation_error_from_database_error(e, model):
    if hasattr(e, 'orig'):
        if hasattr(e.orig, 'args') and hasattr(e.orig.args, '__getitem__'):
            if len(e.orig.args) == 1:
                message = e.orig.args[0]
            elif len(e.orig.args) == 2:
                message = e.orig.args[1]
            else:
                message = e.orig.args

            message = six.text_type(message)

            regex = [
                [r'Key\s\((.+)\)=\((.+)\)\salready\sexists', 1, 2],  # PostgreSQL
                [r'Duplicate\sentry\s\'(.+)\'\sfor key\s\'(.+)\'', 2, 1],  # MySQL
                [r'UNIQUE\sconstraint\sfailed\:\s(.+)\.(.+)', 2, None]  # SQLite
            ]

            for (r, field_index, value_index) in regex:
                match = re.search(r, message, re.IGNORECASE | re.MULTILINE)

                if match:
                    mapper = inspect_uniform(model)
                    columns = dict(map(lambda x: (x.key, x), mapper.columns))
                    column_name = match.group(field_index)

                    if column_name in columns:
                        error = dict()
                        error[column_name] = ValidationError('record with the same value already exists')
                        return ValidationError(error)

            return ValidationError(message)
    return ValidationError('Query failed')
