import inspect, re
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

import six
from django.apps import apps
from django.conf import settings as django_settings
from django.contrib.contenttypes.fields import GenericRel, GenericForeignKey, GenericRelation
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

        try:
            from django.core.files.storage import storages
            self.media_storage = storages[settings.JET_MEDIA_FILE_STORAGE]
        except ImportError:
            from django.core.files.storage import get_storage_class
            self.media_storage = get_storage_class(settings.JET_MEDIA_FILE_STORAGE)()

        self.pool = ThreadPoolExecutor()

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
            'AUTO_OPEN_REGISTER': settings.JET_AUTO_OPEN_REGISTER,
            'CONFIG': settings.JET_CONFIG,
            'WEB_BASE_URL': settings.JET_BACKEND_WEB_BASE_URL,
            'API_BASE_URL': settings.JET_BACKEND_API_BASE_URL,
            'PROJECT': settings.JET_PROJECT,
            'TOKEN': settings.JET_TOKEN,
            'ENVIRONMENT': settings.JET_ENVIRONMENT,
            'CORS_HEADERS': settings.JET_CORS_HEADERS,
            'BASE_URL': settings.JET_BASE_URL,
            'JWT_VERIFY_KEY': settings.JET_JWT_VERIFY_KEY,
            'BEARER_AUTH_KEY': settings.JET_BEARER_AUTH_KEY,
            'ENVIRONMENT_TYPE': settings.JET_ENVIRONMENT_TYPE,
            'BLACKLIST_HOSTS': settings.JET_BLACKLIST_HOSTS,
            'DATABASE_ENGINE': settings.database_engine,
            'DATABASE_HOST': settings.database_settings.get('HOST'),
            'DATABASE_PORT': settings.database_settings.get('PORT'),
            'DATABASE_USER': settings.database_settings.get('USER'),
            'DATABASE_PASSWORD': settings.database_settings.get('PASSWORD'),
            'DATABASE_NAME': str(settings.database_settings['NAME'])
                if settings.database_settings.get('NAME') is not None else None,
            'DATABASE_EXTRA': settings.JET_DATABASE_EXTRA,
            'DATABASE_CONNECTIONS': 1,
            'DATABASE_CONNECTIONS_OVERFLOW': 1,
            'DATABASE_ONLY': settings.JET_DATABASE_ONLY,
            'DATABASE_EXCEPT': settings.JET_DATABASE_EXCEPT,
            'DATABASE_MAX_TABLES': settings.JET_DATABASE_MAX_TABLES,
            'DATABASE_SCHEMA': settings.JET_DATABASE_SCHEMA,
            'DATABASE_REFLECT_MAX_RECORDS': settings.JET_DATABASE_REFLECT_MAX_RECORDS,
            'DATABASE_SSL_CA': settings.JET_DATABASE_SSL_CA,
            'DATABASE_SSL_CERT': settings.JET_DATABASE_SSL_CERT,
            'DATABASE_SSL_KEY': settings.JET_DATABASE_SSL_KEY,
            'DATABASE_SSH_HOST': settings.JET_DATABASE_SSH_HOST,
            'DATABASE_SSH_PORT': settings.JET_DATABASE_SSH_PORT,
            'DATABASE_SSH_USER': settings.JET_DATABASE_SSH_USER,
            'DATABASE_SSH_PRIVATE_KEY': settings.JET_DATABASE_SSH_PRIVATE_KEY,
            'COOKIE_SAMESITE': settings.JET_COOKIE_SAMESITE,
            'COOKIE_SECURE': settings.JET_COOKIE_SECURE,
            'COOKIE_DOMAIN': settings.JET_COOKIE_DOMAIN,
            'COOKIE_COMPRESS': settings.JET_COOKIE_COMPRESS,
            'STORE_PATH': settings.JET_STORE_PATH,
            'CACHE_METADATA': settings.JET_CACHE_METADATA,
            'CACHE_METADATA_PATH': settings.JET_CACHE_METADATA_PATH,
            'CACHE_MODEL_DESCRIPTIONS': settings.JET_CACHE_MODEL_DESCRIPTIONS,
            'SSO_APPLICATIONS': self.clean_sso_applications(settings.JET_SSO_APPLICATIONS),
            'ALLOW_ORIGIN': settings.JET_ALLOW_ORIGIN,
            'TRACK_DATABASES': settings.JET_TRACK_DATABASES,
            'TRACK_DATABASES_ENDPOINT': settings.JET_TRACK_DATABASES_ENDPOINT,
            'TRACK_DATABASES_AUTH': settings.JET_TRACK_DATABASES_AUTH,
            'TRACK_MODELS_ENDPOINT': settings.JET_TRACK_MODELS_ENDPOINT,
            'TRACK_MODELS_AUTH': settings.JET_TRACK_MODELS_AUTH,
            'TRACK_QUERY_SLOW_TIME': settings.JET_TRACK_QUERY_SLOW_TIME,
            'TRACK_QUERY_HIGH_MEMORY': settings.JET_TRACK_QUERY_HIGH_MEMORY,
            'DISABLE_AUTH': settings.JET_DISABLE_AUTH
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
        if not Model or not hasattr(Model, '_meta'):
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

    def run_async(self, func, *args, **kwargs):
        self.pool.submit(func, *args, **kwargs)
