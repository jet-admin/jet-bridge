from jet_bridge_base import status
from jet_bridge_base.db import get_mapped_base, get_engine, reload_mapped_base
from jet_bridge_base.exceptions.not_found import NotFound
from jet_bridge_base.exceptions.validation_error import ValidationError
from jet_bridge_base.permissions import HasProjectPermissions
from jet_bridge_base.responses.json import JSONResponse
from jet_bridge_base.serializers.table import TableSerializer
from jet_bridge_base.views.base.api import APIView
from jet_bridge_base.views.table_column import map_dto_column
from sqlalchemy import Table


class TableView(APIView):
    permission_classes = (HasProjectPermissions,)

    def get_db(self, request):
        MappedBase = get_mapped_base(request)
        engine = get_engine(request)
        return MappedBase.metadata, engine

    def update_base(self, request):
        MappedBase = get_mapped_base(request)
        reload_mapped_base(MappedBase)

    def get_object(self, request):
        metadata, engine = self.get_db(request)
        pk = request.path_kwargs['pk']

        try:
            obj = list(filter(lambda x: x.name == pk, metadata.tables.values()))[0]
        except IndexError:
            raise NotFound

        self.check_object_permissions(request, obj)

        return obj

    def create(self, request, *args, **kwargs):
        serializer = TableSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            self.perform_create(request, serializer)
        except Exception as e:
            raise ValidationError(str(e))

        return JSONResponse(serializer.representation_data, status=status.HTTP_201_CREATED)

    def perform_create(self, request, serializer):
        data = serializer.validated_data
        metadata, engine = self.get_db(request)

        table = Table(
            data['name'],
            metadata,
            *list(map(lambda x: map_dto_column(x, metadata=metadata), data['columns']))
        )

        try:
            table.create(bind=engine)

            metadata.reflect(bind=engine, only=[data['name']])
            self.update_base(request)
        except Exception as e:
            metadata.remove(table)
            raise e

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object(request)
        self.perform_destroy(request, instance)
        return JSONResponse(status=status.HTTP_204_NO_CONTENT)

    def perform_destroy(self, request, table):
        metadata, engine = self.get_db(request)
        table.drop(bind=engine)

        metadata.remove(table)
        self.update_base(request)
