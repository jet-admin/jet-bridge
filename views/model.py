from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker

from serializers.model import get_model_serializer
from serializers.model_description import ModelDescriptionSerializer
from views.base.api import APIView
from views.mixins.list import ListAPIViewMixin

engine = create_engine('postgresql://postgres:password@localhost:5432/jetty')
Session = sessionmaker(bind=engine)


class ModelHandler(ListAPIViewMixin, APIView):
    serializer_class = ModelDescriptionSerializer

    def map_data_type(self, value):
        for rule in self.data_types:
            if rule['operator'] == 'equals' and value == rule['query']:
                return rule['date_type']
            elif rule['operator'] == 'startswith' and value[:len(rule['query'])] == rule['query']:
                return rule['date_type']
        return self.default_data_type

    def get_serializer_class(self):
        Model = self.get_model()
        return get_model_serializer(Model)

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
