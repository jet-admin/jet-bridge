from jet_bridge_base import fields
from jet_bridge_base.db import get_mapped_base, reload_request_graphql_schema, get_request_connection
from jet_bridge_base.db_types import inspect_uniform
from jet_bridge_base.exceptions.validation_error import ValidationError
from jet_bridge_base.models.model_relation_override import ModelRelationOverrideModel
from jet_bridge_base.serializers.serializer import Serializer
from jet_bridge_base.store import store
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

        mapper = inspect_uniform(Model)

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
        connection = get_request_connection(request)
        draft = bool(request.get_argument('draft', False))

        with store.session() as session:
            with session.begin():
                for item in self.validated_data:
                    set_overrides = sorted(item['relations'], key=lambda x: x['name'])

                    existing_overrides = session.query(ModelRelationOverrideModel).filter(
                        ModelRelationOverrideModel.connection_id == connection['id'],
                        ModelRelationOverrideModel.model == item['model'],
                        draft == draft
                    ).order_by(ModelRelationOverrideModel.name).all()
                    existing_overrides = list(existing_overrides)

                    for i, override in enumerate(set_overrides):
                        existing_override = existing_overrides[i] if i < len(existing_overrides) else None

                        if existing_override:
                            existing_override.name = override.get('name')
                            existing_override.direction = override.get('direction')
                            existing_override.local_field = override.get('local_field')
                            existing_override.related_model = override.get('related_model')
                            existing_override.related_field = override.get('related_field')
                        else:
                            session.add(ModelRelationOverrideModel(
                                connection_id=connection['id'],
                                model=item['model'],
                                draft=draft,
                                name=override.get('name'),
                                direction=override.get('direction'),
                                local_field=override.get('local_field'),
                                related_model=override.get('related_model'),
                                related_field=override.get('related_field')
                            ))

                    delete_overrides = existing_overrides[len(item['relations']):]
                    for override in delete_overrides:
                        session.delete(override)

        reload_request_graphql_schema(request, draft)
