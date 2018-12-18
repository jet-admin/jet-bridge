from sqlalchemy import create_engine, MetaData, inspect
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker

from serializers import Serializer, CharField, BooleanField
from serializers.model_description import ModelDescriptionSerializer
from views import APIView, ListAPIViewMixin

engine = create_engine('postgresql://postgres:password@localhost:5432/jetty')
Session = sessionmaker(bind=engine)


class ModelHandler(ListAPIViewMixin, APIView):
    serializer_class = ModelDescriptionSerializer
    data_types = [
        {'query': 'VARCHAR', 'operator': 'startswith', 'date_type': CharField},
        {'query': 'TEXT', 'operator': 'equals', 'date_type': CharField},
        {'query': 'BOOLEAN', 'operator': 'equals', 'date_type': BooleanField},
        {'query': 'INTEGER', 'operator': 'equals', 'date_type': CharField},
        {'query': 'SMALLINT', 'operator': 'equals', 'date_type': CharField},
        {'query': 'NUMERIC', 'operator': 'startswith', 'date_type': CharField},
        {'query': 'VARCHAR', 'operator': 'startswith', 'date_type': CharField},
        {'query': 'TIMESTAMP', 'operator': 'startswith', 'date_type': CharField},
    ]
    default_data_type = CharField

    def map_data_type(self, value):
        for rule in self.data_types:
            if rule['operator'] == 'equals' and value == rule['query']:
                return rule['date_type']
            elif rule['operator'] == 'startswith' and value[:len(rule['query'])] == rule['query']:
                return rule['date_type']
        return self.default_data_type

    def get_serializer_class(self):
        Model = self.get_model()
        mapper = inspect(Model)

        def map_column(column):
            date_type = self.map_data_type(str(column.type))
            return (column.key, date_type())

        class ModelSerializer(Serializer):
            class Meta:
                dynamic_fields = dict(map(map_column, mapper.columns))

        return ModelSerializer

    def get_model(self):
        metadata = MetaData()
        metadata.reflect(engine)
        Base = automap_base(metadata=metadata)

        Base.prepare()
        Model = Base.classes[self.kwargs['model']]

        return Model

    def get_queryset(self):
        session = Session()
        Model = self.get_model()

        return session.query(Model)
