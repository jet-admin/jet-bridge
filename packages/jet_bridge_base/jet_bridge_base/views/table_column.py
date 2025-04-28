import json

from jet_bridge_base.encoders import JSONEncoder
from jet_bridge_base.utils.classes import issubclass_safe, is_instance_or_subclass
from sqlalchemy import Column, text, ForeignKey
from sqlalchemy.exc import DBAPIError, SQLAlchemyError
from sqlalchemy.sql.ddl import AddConstraint, DropConstraint
from sqlalchemy.sql import sqltypes

from jet_bridge_base import status
from jet_bridge_base.db import get_mapped_base, get_engine, reload_request_mapped_base
from jet_bridge_base.exceptions.not_found import NotFound
from jet_bridge_base.exceptions.validation_error import ValidationError
from jet_bridge_base.permissions import HasProjectPermissions
from jet_bridge_base.responses.json import JSONResponse
from jet_bridge_base.serializers.table import TableColumnSerializer
from jet_bridge_base.utils.db_types import map_to_sql_type, db_to_sql_type, get_sql_type_convert
from jet_bridge_base.views.base.api import APIView
from jet_bridge_base.views.model_description import map_table_column


def map_dto_column(table_name, column, metadata):
    args = []
    column_kwargs = {}
    autoincrement = False
    server_default = None
    db_type = column.get('db_field')
    map_type = column.get('field')
    column_type = db_to_sql_type(db_type) if db_type else map_to_sql_type(map_type)

    if column.get('primary_key', False):
        autoincrement = True

    if 'default_type' in column:
        if column['default_type'] == 'value':
            server_default = column['default_value']

            if isinstance(server_default, bool):
                server_default = '1' if server_default else '0'
        elif column['default_type'] == 'datetime_now':
            server_default = text('NOW()')
        elif column['default_type'] == 'uuid':
            server_default = text("uuid_generate_v4()")
        elif column['default_type'] == 'sequence':
            server_default = text("nextval({})".format(column['default_value']))
        elif column['default_type'] == 'auto_increment':
            autoincrement = True

    params = column.get('params')
    if params:
        if 'length' in params:
            column_kwargs['length'] = params['length']

    try:
        from geoalchemy2 import types
        if column_type is types.Geography:
            column_kwargs['geometry_type'] = 'POINT'
    except ImportError:
        pass

    if issubclass_safe(column_type, sqltypes.DateTime):
        column_kwargs['timezone'] = True

    if callable(column_type):
        try:
            column_type = column_type(**column_kwargs)
        except TypeError:
            pass

    if params:
        if 'related_model' in params:
            model = params['related_model'].get('model')

            try:
                table = list(filter(lambda x: x.name == model, metadata.tables.values()))[0]

                table_primary_keys = table.primary_key.columns.keys()
                table_primary_key = table_primary_keys[0] if len(table_primary_keys) > 0 else None
                related_column_name = params.get('custom_primary_key') or table_primary_key
                related_column = [x for x in table.columns if x.name == related_column_name][0]
                name = '{}_{}_fkey'.format(table_name, column['name'])

                column_type = related_column.type
                foreign_key = ForeignKey(related_column, name=name)
                args.append(foreign_key)
            except IndexError:
                pass

    data_source_meta = {}
    data_source_field = column.get('data_source_field')
    data_source_name = column.get('data_source_name')
    data_source_params = column.get('data_source_params')

    if data_source_field:
        data_source_meta['field'] = data_source_field

    if data_source_name:
        data_source_meta['name'] = data_source_name

    if data_source_params:
        data_source_meta['params'] = data_source_params

    if len(data_source_meta.keys()):
        comment = json.dumps(data_source_meta, cls=JSONEncoder)
    else:
        comment = None

    return Column(
        *args,
        name=column['name'],
        type_=column_type,
        autoincrement=autoincrement,
        primary_key=column.get('primary_key', False),
        nullable=column.get('null', False),
        server_default=server_default,
        comment=comment
    )


class TableColumnView(APIView):
    permission_classes = (HasProjectPermissions,)

    def get_db(self, request):
        MappedBase = get_mapped_base(request)
        engine = get_engine(request)
        return MappedBase.metadata, engine

    def update_base(self, request):
        reload_request_mapped_base(request)

    def get_table(self, request):
        metadata, engine = self.get_db(request)
        table_name = request.path_kwargs['table']

        try:
            obj = list(filter(lambda x: x.name == table_name, metadata.tables.values()))[0]
        except IndexError:
            raise NotFound

        self.check_object_permissions(request, obj)

        return obj

    def get_object(self, request):
        metadata, engine = self.get_db(request)
        table_name = request.path_kwargs['table']

        try:
            table = list(filter(lambda x: x.name == table_name, metadata.tables.values()))[0]
        except IndexError:
            raise NotFound

        pk = request.path_kwargs['pk']
        obj = table.columns.get(pk)

        if obj is None:
            raise NotFound

        self.check_object_permissions(request, obj)

        return obj

    def list(self, request, *args, **kwargs):
        metadata, engine = self.get_db(request)
        table = self.get_table(request)
        columns = list(map(lambda x: map_table_column(metadata, table, x, True), table.columns))
        return JSONResponse(columns)

    def retrieve(self, request, *args, **kwargs):
        metadata, engine = self.get_db(request)
        instance = self.get_object(request)
        table = instance.table
        return JSONResponse(map_table_column(metadata, table, instance, True))

    def create(self, request, *args, **kwargs):
        serializer = TableColumnSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            self.perform_create(request, serializer)
        except Exception as e:
            if isinstance(e, DBAPIError):
                if '(psycopg2.errors.DuplicateColumn)' in e.args[0]:
                    raise ValidationError('Column with such name already exists')
            raise ValidationError(str(e))

        return JSONResponse(serializer.representation_data, status=status.HTTP_201_CREATED)

    def perform_create(self, request, serializer):
        metadata, engine = self.get_db(request)
        table = self.get_table(request)
        column = map_dto_column(table.name, serializer.validated_data, metadata)
        column._set_parent(table)

        ddl_compiler = engine.dialect.ddl_compiler(engine.dialect, None)
        column_specification = ddl_compiler.get_column_specification(column)

        table_name = ddl_compiler.preparer.format_table(table)
        engine.execute('''ALTER TABLE {0} ADD COLUMN {1}'''.format(table_name, column_specification))

        for foreign_key in column.foreign_keys:
            if not foreign_key.constraint:
                foreign_key._set_table(column, table)
                engine.execute(AddConstraint(foreign_key.constraint))

        self.update_base(request)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object(request)
        self.perform_destroy(request, instance)
        return JSONResponse(status=status.HTTP_204_NO_CONTENT)

    def perform_destroy(self, request, column):
        metadata, engine = self.get_db(request)
        table = self.get_table(request)

        ddl_compiler = engine.dialect.ddl_compiler(engine.dialect, None)
        table_name = ddl_compiler.preparer.format_table(table)
        column_name = ddl_compiler.preparer.format_column(column)
        engine.execute('''ALTER TABLE {0} DROP COLUMN {1}'''.format(table_name, column_name))

        table._columns.remove(column)

        for fk in column.foreign_keys:
            table.foreign_keys.remove(fk)
            if fk.constraint in table.constraints:
                # this might have been removed
                # already, if it's a composite constraint
                # and more than one col being replaced
                table.constraints.remove(fk.constraint)

        self.update_base(request)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object(request)
        serializer = TableColumnSerializer(data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        try:
            self.perform_update(request, instance, serializer)
        except Exception as e:
            if isinstance(e, DBAPIError):
                if '(psycopg2.errors.InvalidDatetimeFormat)' in e.args[0]:
                    raise ValidationError('Some of the rows has invalid date format')
                elif '(psycopg2.errors.DuplicateColumn)' in e.args[0]:
                    raise ValidationError('Column with such name already exists')
            raise ValidationError(str(e))

        return JSONResponse(serializer.representation_data)

    def perform_update(self, request, existing_column, serializer):
        metadata, engine = self.get_db(request)
        table = self.get_table(request)
        existing_data = map_table_column(metadata, table, existing_column, True)
        existing_dto = {
            'name': existing_data['name'],
            'field': existing_data['field'],
            'primary_key': existing_column.table.primary_key.columns[0].name == existing_data['name']
        }

        if 'length' in existing_data:
            existing_dto['length'] = existing_data['length']

        column_data = {
            **existing_dto,
            **serializer.validated_data
        }
        column = map_dto_column(table.name, column_data, metadata)

        ddl_compiler = engine.dialect.ddl_compiler(engine.dialect, None)
        table_name = ddl_compiler.preparer.format_table(table)

        column_name = ddl_compiler.preparer.format_column(column)
        column_type = column.type.compile(engine.dialect)
        column_iterable = is_instance_or_subclass(column.type, sqltypes.Indexable)
        existing_column_name = ddl_compiler.preparer.format_column(existing_column)
        existing_column_type = existing_column.type.compile(engine.dialect)
        existing_column_iterable = is_instance_or_subclass(existing_column.type, sqltypes.Indexable)

        preserve_column_index = None

        if column_name != existing_column_name:
            try:
                preserve_column_index = table._columns.values().index(existing_column)
                table._columns.remove(existing_column)
            except ValueError:
                pass

        column._set_parent(table)

        if preserve_column_index is not None:
            try:
                new_column_index = table._columns.values().index(column)
                columns_collection = table._columns._collection
                columns_collection.insert(preserve_column_index, columns_collection.pop(new_column_index))
            except ValueError:
                pass

        column_type_stmt = column_type
        sql_type_convert = get_sql_type_convert(column.type)

        if not existing_column_iterable and column_iterable:
            column_type_stmt += ''' USING 
                CASE 
                    WHEN {0} IS NULL THEN '[]'::jsonb 
                    ELSE to_jsonb(ARRAY[{0}]) 
                END'''.format(existing_column_name)
        elif sql_type_convert:
            column_type_stmt += ' USING {0}'.format(sql_type_convert(existing_column_name))

        with request.session.begin():
            try:
                for foreign_key in existing_column.foreign_keys:
                    if foreign_key.constraint:
                        foreign_key_should_exist = any(map(lambda x: x.target_fullname == foreign_key.target_fullname, column.foreign_keys))
                        if foreign_key_should_exist:
                            continue
                        request.session.execute(DropConstraint(foreign_key.constraint))

                if column_type != existing_column_type:
                    request.session.execute('''ALTER TABLE {0} ALTER COLUMN {1} DROP DEFAULT'''.format(table_name, existing_column_name))
                    request.session.execute('''ALTER TABLE {0} ALTER COLUMN {1} TYPE {2}'''.format(table_name, existing_column_name, column_type_stmt))

                if column.nullable:
                    request.session.execute('''ALTER TABLE {0} ALTER COLUMN {1} DROP NOT NULL'''.format(table_name, existing_column_name))
                else:
                    request.session.execute('''ALTER TABLE {0} ALTER COLUMN {1} SET NOT NULL'''.format(table_name, existing_column_name))

                default = ddl_compiler.get_column_default_string(column)

                if default is not None:
                    request.session.execute('''ALTER TABLE {0} ALTER COLUMN {1} SET DEFAULT {2}'''.format(table_name, existing_column_name, default))
                else:
                    request.session.execute('''ALTER TABLE {0} ALTER COLUMN {1} DROP DEFAULT'''.format(table_name, existing_column_name))

                column_rename = column_name != existing_column_name

                if column_rename:
                    request.session.execute('''ALTER TABLE {0} RENAME COLUMN {1} TO {2}'''.format(table_name, existing_column_name, column_name))

                for foreign_key in column.foreign_keys:
                    if not foreign_key.constraint:
                        foreign_key_exists = any(map(lambda x: x.target_fullname == foreign_key.target_fullname, existing_column.foreign_keys))
                        if foreign_key_exists:
                            continue
                        foreign_key._set_table(column, table)
                        request.session.execute(AddConstraint(foreign_key.constraint))

                self.update_base(request)
            except SQLAlchemyError as e:
                request.session.rollback()

                table._columns.remove(column)
                existing_column._set_parent(table)

                for fk in column.foreign_keys:
                    table.foreign_keys.remove(fk)
                    if fk.constraint in table.constraints:
                        table.constraints.remove(fk.constraint)

                self.update_base(request)
                raise e

    def partial_update(self, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(*args, **kwargs)
