from sqlalchemy import inspect

from jet_bridge_base import fields
from jet_bridge_base.db import get_mapped_base, reload_request_graphql_schema, connection_store_set, \
    connection_store_get
from jet_bridge_base.exceptions.validation_error import ValidationError
from jet_bridge_base.serializers.serializer import Serializer
from jet_bridge_base.logger import logger


class ModelDescriptionRelationOverrideSerializer(Serializer):
    direction = fields.CharField()
    local_field = fields.CharField()
    related_model = fields.CharField()
    related_field = fields.CharField()


class ModelDescriptionRelationOverridesSerializer(Serializer):
    model = fields.CharField()
    relations = ModelDescriptionRelationOverrideSerializer(many=True)

    def get_model(self, request, name):
        MappedBase = get_mapped_base(request)
        return MappedBase.classes.get(name)

    def generate_many_to_one_name(self, mapper, local_field, related_model, related_field):
        name = '__'.join([local_field, 'to', related_model, related_field])

        if name in mapper.columns:
            name = name + '_relation'
            logger.warning('Already detected column name, using {}'.format(name))

        return name

    def generate_one_to_many_name(self, mapper, local_field, related_model, related_field):
        name = '__'.join([related_model, related_field, 'to', local_field])

        if name in mapper.columns:
            name = name + '_relation'
            logger.warning('Already detected column name, using {}'.format(name))

        return name

    def validate(self, attrs):
        request = self.context.get('request')

        Model = self.get_model(request, attrs['model'])
        if Model is None:
            raise ValidationError('Unknown relation override model: {}'.format(attrs['model']))

        mapper = inspect(Model)

        for item in attrs['relations']:
            if item['direction'] == 'MANYTOONE':
                item['name'] = self.generate_many_to_one_name(mapper, item['local_field'], item['related_model'], item['related_field'])
            elif item['direction'] == 'ONETOMANY':
                item['name'] = self.generate_one_to_many_name(mapper, item['local_field'], item['related_model'], item['related_field'])
            else:
                raise ValidationError('Unknown relation direction: {}'.format(item['direction']))

        return attrs

    def save(self):
        request = self.context.get('request')
        draft = request.get_argument('draft', False)

        relationships_overrides_key = 'relation_overrides_draft' if draft else 'relation_overrides'
        relationships_overrides = connection_store_get(request, relationships_overrides_key, {})

        for item in self.validated_data:
            relationships_overrides[item['model']] = list(map(lambda x: {
                'name': x.get('name'),
                'direction': x.get('direction'),
                'local_field': x.get('local_field'),
                'related_model': x.get('related_model'),
                'related_field': x.get('related_field')
            }, item['relations']))

        connection_store_set(request, relationships_overrides_key, relationships_overrides)
        reload_request_graphql_schema(request)
