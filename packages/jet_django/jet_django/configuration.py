from django.apps import apps
from django.conf import settings as django_settings
from django.contrib.contenttypes.fields import GenericRel, GenericForeignKey, GenericRelation
from django.core.files.storage import get_storage_class
from django.db import models

from jet_bridge_base.configuration import Configuration

from jet_django import settings, VERSION


class JetDjangoConfiguration(Configuration):
    models = dict()
    media_storage = None

    def __init__(self):
        models = apps.get_models()
        self.models = dict(map(lambda x: (self.model_key(x), self.serialize_model(x)), models))

        for model in models:
            for related_model in self.get_related_models(model):
                if self.model_key(related_model) in self.models:
                    continue
                self.models[self.model_key(related_model)] = self.serialize_model(related_model)

        self.media_storage = get_storage_class(settings.JET_MEDIA_FILE_STORAGE)()

    def get_version(self):
        return VERSION

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

    def media_get_available_name(self, path):
        return self.media_storage.get_available_name(path)

    def media_exists(self, path):
        return self.media_storage.exists(path)

    def media_listdir(self, path):
        return self.media_storage.listdir(path)

    def media_get_modified_time(self, path):
        return self.media_storage.get_modified_time(path)

    def media_size(self, path):
        return self.media_storage.size(path)

    def media_open(self, path, mode='rb'):
        return self.media_storage.open(path, mode)

    def media_save(self, path, content):
        return self.media_storage.save(path, content)

    def media_delete(self, path):
        self.media_storage.delete(path)

    def media_url(self, path, request):
        url = '{}{}'.format(django_settings.MEDIA_URL, path)

        if not django_settings.MEDIA_URL.startswith('http://') and not django_settings.MEDIA_URL.startswith('https://'):
            url = '{}://{}{}'.format(request.protocol, request.host, url)

        return url
