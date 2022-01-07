from sqlalchemy import Column, text

from jet_bridge_base import status
from jet_bridge_base.db import get_mapped_base, get_engine, reload_mapped_base
from jet_bridge_base.exceptions.not_found import NotFound
from jet_bridge_base.exceptions.validation_error import ValidationError
from jet_bridge_base.permissions import HasProjectPermissions
from jet_bridge_base.responses.json import JSONResponse
from jet_bridge_base.serializers.table import TableColumnSerializer
from jet_bridge_base.utils.db_types import map_query_type
from jet_bridge_base.views.base.api import APIView
from jet_bridge_base.views.model_description import map_column


def map_dto_column(column):
    column_kwargs = {}
    autoincrement = False
    server_default = None

    if column.get('primary_key', False):
        autoincrement = True

    if 'length' in column:
        column_kwargs['length'] = column['length']

    if 'default_type' in column:
        if column['default_type'] == 'value':
            server_default = column['default_value']
        elif column['default_type'] == 'datetime_now':
            server_default = text('NOW()')
        elif column['default_type'] == 'uuid':
            server_default = text("uuid_generate_v4()")
        elif column['default_type'] == 'auto_increment':
            autoincrement = True

    column_type = map_query_type(column['field'])

    if callable(column_type):
        try:
            column_type = column_type(**column_kwargs)
        except TypeError:
            pass

    return Column(
        column['name'],
        column_type,
        autoincrement=autoincrement,
        primary_key=column.get('primary_key', False),
        nullable=column.get('null', False),
        server_default=server_default
    )


class TableColumnView(APIView):
    permission_classes = (HasProjectPermissions,)

    def get_db(self, request):
        MappedBase = get_mapped_base(request)
        engine = get_engine(request)
        return MappedBase.metadata, engine

    def update_base(self, request):
        MappedBase = get_mapped_base(request)
        reload_mapped_base(MappedBase)

    def get_table(self, request):
        metadata, engine = self.get_db(request)
        table = request.path_kwargs['table']
        obj = metadata.tables.get(table)

        if obj is None:
            raise NotFound

        self.check_object_permissions(request, obj)

        return obj

    def get_object(self, request):
        metadata, engine = self.get_db(request)
        table_name = request.path_kwargs['table']
        table = metadata.tables.get(table_name)

        if table is None:
            raise NotFound

        pk = request.path_kwargs['pk']
        obj = table.columns.get(pk)

        if obj is None:
            raise NotFound

        self.check_object_permissions(request, obj)

        return obj

    def list(self, request, *args, **kwargs):
        table = self.get_table(request)
        columns = list(map(lambda x: map_column(x, True), table.columns))
        return JSONResponse(columns)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object(request)
        return JSONResponse(map_column(instance, True))

    def create(self, request, *args, **kwargs):
        serializer = TableColumnSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            self.perform_create(request, serializer)
        except Exception as e:
            raise ValidationError(str(e))

        return JSONResponse(serializer.representation_data, status=status.HTTP_201_CREATED)

    def perform_create(self, request, serializer):
        metadata, engine = self.get_db(request)
        table = self.get_table(request)
        column = map_dto_column(serializer.validated_data)

        ddl_compiler = engine.dialect.ddl_compiler(engine.dialect, None)
        column_specification = ddl_compiler.get_column_specification(column)

        engine.execute('''ALTER TABLE "{0}" ADD COLUMN {1}'''.format(table.name, column_specification))

        metadata.remove(table)
        metadata.reflect(bind=engine, only=[table.name])
        self.update_base(request)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object(request)
        self.perform_destroy(request, instance)
        return JSONResponse(status=status.HTTP_204_NO_CONTENT)

    def perform_destroy(self, request, column):
        metadata, engine = self.get_db(request)
        table = self.get_table(request)
        engine.execute('''ALTER TABLE "{0}" DROP COLUMN "{1}" '''.format(table.name, column.name))

        metadata.remove(table)
        metadata.reflect(bind=engine, only=[table.name])
        self.update_base(request)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object(request)
        serializer = TableColumnSerializer(instance=instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        try:
            self.perform_update(request, serializer)
        except Exception as e:
            raise ValidationError(str(e))

        return JSONResponse(serializer.representation_data)

    def perform_update(self, request, serializer):
        metadata, engine = self.get_db(request)
        table = self.get_table(request)
        existing_data = map_column(serializer.instance, True)
        existing_dto = {
            'name': existing_data['name'],
            'field': existing_data['field'],
            'primary_key': serializer.instance.table.primary_key.columns[0].name == existing_data['name']
        }

        if 'length' in existing_data:
            existing_dto['length'] = existing_data['length']

        column = map_dto_column({
            **existing_dto,
            **serializer.validated_data
        })

        column_name = serializer.instance.name
        column_type = column.type.compile(engine.dialect)

        engine.execute('''ALTER TABLE "{0}" ALTER COLUMN "{1}" TYPE {2}'''.format(table.name, column_name, column_type))
        # engine.execute('ALTER TABLE {0} ALTER COLUMN {1} TYPE {2} USING {1}::integer'.format(table.name, column_name, column_type))

        if column.nullable:
            engine.execute('''ALTER TABLE "{0}" ALTER COLUMN "{1}" DROP NOT NULL'''.format(table.name, column_name))
        else:
            engine.execute('''ALTER TABLE "{0}" ALTER COLUMN "{1}" SET NOT NULL'''.format(table.name, column_name))

        ddl_compiler = engine.dialect.ddl_compiler(engine.dialect, None)
        default = ddl_compiler.get_column_default_string(column)

        if default is not None:
            engine.execute('''ALTER TABLE "{0}" ALTER COLUMN "{1}" SET DEFAULT {2}'''.format(table.name, column_name, default))
        else:
            engine.execute('''ALTER TABLE "{0}" ALTER COLUMN "{1}" DROP DEFAULT'''.format(table.name, column_name))

        if column_name != column.name:
            engine.execute('''ALTER TABLE "{0}" RENAME COLUMN "{1}" TO "{2}"'''.format(table.name, column_name, column.name))

        metadata.remove(table)
        metadata.reflect(bind=engine, only=[table.name])
        self.update_base(request)

    def partial_update(self, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(*args, **kwargs)
