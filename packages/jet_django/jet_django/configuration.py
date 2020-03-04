import inspect, re
from datetime import datetime

import six
from django.apps import apps
from django.conf import settings as django_settings
from django.contrib.contenttypes.fields import GenericRel, GenericForeignKey, GenericRelation
from django.core.files.storage import get_storage_class
from django.db import models
from django.db.models.signals import post_save, post_delete, pre_save, pre_delete
from django.utils import timezone

from jet_bridge_base.configuration import Configuration
from jet_bridge_base.logger import logger

from jet_django import settings, VERSION


class JetDjangoConfiguration(Configuration):
    models = dict()
    model_classes = dict()
    media_storage = None
    pre_delete_django_instance = None

    def __init__(self):
        models = apps.get_models()
        self.model_classes = dict(map(lambda x: (x._meta.db_table, x), models))
        self.models = dict(map(lambda x: (self.model_key(x), self.serialize_model(x)), models))

        for model in models:
            for related_model in self.get_related_models(model):
                if self.model_key(related_model) in self.models:
                    continue
                self.models[self.model_key(related_model)] = self.serialize_model(related_model)

        self.media_storage = get_storage_class(settings.JET_MEDIA_FILE_STORAGE)()

    def get_type(self):
        return 'jet_django'

    def get_version(self):
        return VERSION

    def get_model_description(self, db_table):
        return self.models.get(db_table)

    def get_hidden_model_description(self):
        return ['__jet__token', 'jet_django_token', 'django_migrations']

    def get_settings(self):
        return {
            'DEBUG': django_settings.DEBUG,
            'READ_ONLY': settings.JET_READ_ONLY,
            'WEB_BASE_URL': settings.JET_BACKEND_WEB_BASE_URL,
            'API_BASE_URL': settings.JET_BACKEND_API_BASE_URL,
            'PROJECT': settings.JET_PROJECT,
            'TOKEN': settings.JET_TOKEN,
            'CORS_HEADERS': settings.JET_CORS_HEADERS,
            'DATABASE_ENGINE': settings.database_engine,
            'DATABASE_HOST': settings.database_settings.get('HOST'),
            'DATABASE_PORT': settings.database_settings.get('PORT'),
            'DATABASE_USER': settings.database_settings.get('USER'),
            'DATABASE_PASSWORD': settings.database_settings.get('PASSWORD'),
            'DATABASE_NAME': settings.database_settings.get('NAME'),
            'DATABASE_EXTRA': settings.JET_DATABASE_EXTRA,
            'DATABASE_CONNECTIONS': 1,
            'DATABASE_ONLY': settings.JET_DATABASE_ONLY,
            'DATABASE_EXCEPT': settings.JET_DATABASE_EXCEPT,
            'DATABASE_SCHEMA': settings.JET_DATABASE_SCHEMA
        }

    def get_django_instance(self, model, instance):
        model_cls = self.model_classes.get(model)
        pk = model_cls._meta.pk.column
        if getattr(instance, pk):
            return model_cls, model_cls.objects.get(pk=getattr(instance, pk))
        else:
            django_instance = model_cls()
            for field in self.get_model_fields(model_cls):
                setattr(django_instance, field.name, getattr(instance, field.get_attname_column()[1]))
            return model_cls, django_instance

    def on_model_pre_create(self, model, instance):
        try:
            model_cls, django_instance = self.get_django_instance(model, instance)
            pre_save.send(model_cls, raw=True, using=self, instance=django_instance, update_fields=[])
        except Exception as e:
            logger.warning('[!] on_model_pre_create signal failed: {}'.format(str(e)))

    def on_model_post_create(self, model, instance):
        try:
            model_cls, django_instance = self.get_django_instance(model, instance)
            post_save.send(model_cls, raw=True, using=self, instance=django_instance, created=True, update_fields=[])
        except Exception as e:
            logger.warning('[!] on_model_post_create signal failed: {}'.format(str(e)))

    def on_model_pre_update(self, model, instance):
        try:
            model_cls, django_instance = self.get_django_instance(model, instance)
            pre_save.send(model_cls, raw=True, using=self, instance=django_instance, update_fields=[])
        except Exception as e:
            logger.warning('[!] on_model_pre_update signal failed: {}'.format(str(e)))

    def on_model_post_update(self, model, instance):
        try:
            model_cls, django_instance = self.get_django_instance(model, instance)
            post_save.send(model_cls, raw=True, using=self, instance=django_instance, created=False, update_fields=[])
        except Exception as e:
            logger.warning('[!] on_model_post_update signal failed: {}'.format(str(e)))

    def on_model_pre_delete(self, model, instance):
        try:
            model_cls, django_instance = self.get_django_instance(model, instance)
            pre_delete.send(model_cls, using=self, instance=django_instance)
            self.pre_delete_django_instance = django_instance
        except Exception as e:
            logger.warning('[!] on_model_pre_delete signal failed: {}'.format(str(e)))

    def on_model_post_delete(self, model, instance):
        try:
            model_cls = self.model_classes.get(model)
            post_delete.send(model_cls, using=self, instance=self.pre_delete_django_instance)
        except Exception as e:
            logger.warning('[!] on_model_post_delete signal failed: {}'.format(str(e)))

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

    def field_db_column_from_name(self, name, fields):
        for f in fields:
            if f.name != name:
                continue
            return f.get_attname_column()[1]

    def guess_display_field(self, model, fields):
        str_method = None
        str_methods = ['__str__', '__unicode__']

        for m in str_methods:
            if hasattr(model, m):
                str_method = m
                break

        if str_method is None:
            return

        source_code = inspect.getsource(getattr(model, str_method))
        regexes = [
            r'return\s+self\.(\w+)',
            r'return\s+str\(self\.(\w+)\)',
            r'return\s+text_type\(self\.(\w+)\)',
            r'return\su?\'%[sd]\'\s+%\s+self\.(\w+)',
            r'return\s+u?\'\{0?\}\'\.format\(self.(\w+)\)',
        ]

        for regex in regexes:
            m = re.search(regex, source_code)
            if not m:
                continue
            field_name = m.group(1)
            return self.field_db_column_from_name(field_name, fields)

    def serialize_model(self, model):
        fields = list(self.get_model_fields(model))

        result = {
            'model': model._meta.db_table,
            'verbose_name': self.serializable(model._meta.verbose_name),
            'verbose_name_plural': self.serializable(model._meta.verbose_name_plural),
            'fields': list(map(lambda field: self.serialize_field(field), fields))
        }

        if hasattr(model._meta, 'ordering') and model._meta.ordering:
            ordering = model._meta.ordering[0]
            desc = ordering.startswith('-')
            field_name = ordering[1:] if desc else ordering

            if '__' not in field_name:
                field_name = self.field_db_column_from_name(field_name, fields)
                if field_name:
                    result['default_order_by'] = '-' + field_name if desc else field_name

        display_field = self.guess_display_field(model, fields)
        if display_field:
            result['display_field'] = display_field

        return result

    def serialize_field(self, field):
        result = {
            'db_column': field.get_attname_column()[1],
            'verbose_name': self.serializable(field.verbose_name),
            'field': field.__class__.__name__,
            'required': not field.blank,
            'editable': field.editable
        }
        
        if hasattr(field, 'related_model') and field.related_model:
            result['params'] = {'related_model': self.serialize_related_model(field.related_model)}

        if field.default == timezone.now \
                or field.default == datetime.now \
                or getattr(field, 'auto_now', False) \
                or getattr(field, 'auto_now_add', False):
            result['default_type'] = 'datetime_now'
        elif field.default is None or isinstance(field.default, (str, bool, int, float)):
            result['default_type'] = 'value'
            result['default_value'] = field.default

        if hasattr(field, 'choices') and field.choices and len(field.choices) > 0:
            result['field'] = 'SelectField'
            result['params'] = {
                'options': list(map(lambda x: {
                    'value': self.serializable(x[0]),
                    'name': six.text_type(x[1])
                }, field.choices))
            }

        if not field.editable and not field.null and result.get('default_type') is None:
            result['editable'] = True

        return result

    def serializable(self, value):
        if value is None:
            return value
        if not isinstance(value, (str, bool, int, float)):
            return six.text_type(value)
        return value

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
        directories = []
        files = []

        dirnames, filenames = self.media_storage.listdir(path)
        directories.extend(dirnames)
        files.extend(filenames)

        for dirname in dirnames:
            directories_inner, files_inner = self.media_listdir(dirname)
            directories.extend(directories_inner)
            files.extend(files_inner)

        return directories, files

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
