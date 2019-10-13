from django.apps import apps
from django.conf import settings as django_settings
from django.db import models
from django.contrib.contenttypes.fields import GenericRel, GenericForeignKey, GenericRelation

from jet_bridge_base.configuration import Configuration
from jet_django import settings


class JetDjangoConfiguration(Configuration):
    models = dict()

    def __init__(self):
        models = apps.get_models()
        self.models = dict(map(lambda x: (self.model_key(x), self.serialize_model(x)), models))

        for model in models:
            for related_model in self.get_related_models(model):
                if self.model_key(related_model) in self.models:
                    continue
                self.models[self.model_key(related_model)] = self.serialize_model(related_model)

    def get_model_description(self, db_table):
        return self.models.get(db_table)

    def get_hidden_model_description(self):
        return ['__jet__token', 'jet_django_token', 'django_migrations']

    def get_settings(self):
        return {
            'BRIDGE_TYPE': 'jet_django',
            'DEBUG': django_settings.DEBUG,
            'READ_ONLY': settings.JET_READ_ONLY,
            'WEB_BASE_URL': settings.JET_BACKEND_WEB_BASE_URL,
            'API_BASE_URL': settings.JET_BACKEND_API_BASE_URL,
            # 'MEDIA_STORAGE': MEDIA_STORAGE,
            # 'MEDIA_ROOT': MEDIA_ROOT,
            # 'MEDIA_BASE_URL': MEDIA_BASE_URL,
            'DATABASE_ENGINE': settings.database_engine,
            'DATABASE_HOST': settings.database_settings.get('HOST'),
            'DATABASE_PORT': settings.database_settings.get('PORT'),
            'DATABASE_USER': settings.database_settings.get('USER'),
            'DATABASE_PASSWORD': settings.database_settings.get('PASSWORD'),
            'DATABASE_NAME': settings.database_settings.get('NAME'),
            # 'DATABASE_EXTRA': DATABASE_EXTRA,
            'DATABASE_CONNECTIONS': 1
        }

    def model_key(self, model):
        return model._meta.db_table

    def get_related_models(self, model):
        fields = model._meta.get_fields(include_hidden=True)
        def filter_fields(x):
            if any(map(lambda rel: isinstance(x, rel), [
                models.OneToOneRel,
                models.OneToOneField,
                models.ManyToOneRel,
                models.ManyToManyField,
                models.ManyToManyRel
            ])):
                return True
            return False
        return list(map(lambda x: x.related_model, filter(filter_fields, fields)))

    def serialize_model(self, model):
        return {
            'model': model._meta.db_table,
            'verbose_name': model._meta.verbose_name,
            'verbose_name_plural': model._meta.verbose_name_plural,
            'fields': list(map(lambda field: self.serialize_field(field), self.get_model_fields(model)))
        }
    
    def serialize_field(self, field):
        result = {
            'verbose_name': field.verbose_name,
            'field': field.__class__.__name__,
            'required': not field.blank,
            'editable': field.editable
        }
        
        if hasattr(field, 'related_model') and field.related_model:
            result['params'] = {'related_model': self.serialize_related_model(field.related_model)}
            
        return result

    def serialize_related_model(self, Model):
        if not Model:
            return
        return {
            'model': Model._meta.db_table,
        }

    def get_model_fields(self, model):
        fields = model._meta.get_fields()

        def filter_fields(x):
            if any(map(lambda rel: isinstance(x, rel), [
                models.ManyToOneRel,
                models.ManyToManyField,
                models.ManyToManyRel,
                GenericRel,
                GenericForeignKey,
                GenericRelation
            ])):
                return False
            return True
        return filter(filter_fields, fields)
