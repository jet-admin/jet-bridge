from sqlalchemy import inspect

from jet_bridge_base import fields
from jet_bridge_base.db import get_mapped_base, connection_cache_set, reload_request_graphql_schema, \
    connection_storage_set, connection_storage_get
from jet_bridge_base.exceptions.validation_error import ValidationError
from jet_bridge_base.serializers.serializer import Serializer
from jet_bridge_base.logger import logger


class RelationshipOverrideSerializer(Serializer):
    model = fields.CharField()
    direction = fields.CharField()
    local_field = fields.CharField()
    related_model = fields.CharField()
    related_field = fields.CharField()

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

        if attrs['direction'] == 'MANYTOONE':
            attrs['name'] = self.generate_many_to_one_name(mapper, attrs['local_field'], attrs['related_model'], attrs['related_field'])
        elif attrs['direction'] == 'ONETOMANY':
            attrs['name'] = self.generate_one_to_many_name(mapper, attrs['local_field'], attrs['related_model'], attrs['related_field'])
        else:
            raise ValidationError('Unknown relation direction: {}'.format(attrs['direction']))

        return attrs

    def save(self):
        request = self.context.get('request')
        draft = request.get_argument('draft', False)

        relationships_overrides_key = 'relation_overrides_draft' if draft else 'relation_overrides'
        relationships_overrides = connection_storage_get(request, relationships_overrides_key, {})

        for override in self.validated_data:
            if override['model'] not in relationships_overrides:
                relationships_overrides[override['model']] = []

            relationships_overrides[override['model']].append({
                'name': override.get('name'),
                'direction': override.get('direction'),
                'local_field': override.get('local_field'),
                'related_model': override.get('related_model'),
                'related_field': override.get('related_field')
            })


        connection_storage_set(request, relationships_overrides_key, relationships_overrides)
        reload_request_graphql_schema(request)
