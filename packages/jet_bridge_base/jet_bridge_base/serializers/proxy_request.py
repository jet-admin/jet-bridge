import json
import re

import requests
from jet_bridge_base import fields, settings
from jet_bridge_base.configuration import configuration
from jet_bridge_base.exceptions.validation_error import ValidationError
from jet_bridge_base.responses.base import Response
from jet_bridge_base.serializers.serializer import Serializer
from jet_bridge_base.utils.backend import get_resource_secret_tokens, get_secret_tokens


class ProxyRequestSerializer(Serializer):
    method = fields.CharField(required=False, default='GET')
    url = fields.CharField(trim_whitespace=False)
    query_params = fields.JSONField(required=False, default=dict)
    headers = fields.JSONField(required=False, default=dict)
    body = fields.RawField(required=False)

    project = fields.CharField(required=False)
    resource = fields.CharField(required=False)
    secret_tokens = fields.CharField(required=False)
    context = fields.JSONField(required=False)

    def resolve_secret_tokens(self, names, project, resource):
        request = self.context.get('request')
        instances = {}
        unresolved = names[:]

        for name in unresolved:
            regex = re.search('sso\.(?P<sso>\w+)\.(?P<token>\w+)', name)

            if not regex:
                continue

            matches = regex.groupdict()

            if matches['token'] != 'access_token':
                continue

            app = configuration.clean_sso_application_name(matches['sso'])
            config = settings.SSO_APPLICATIONS.get(app)

            if not config:
                continue

            extra_data_key = '_'.join(['extra_data', app])

            try:
                extra_data_str = configuration.session_get(request, extra_data_key)
                extra_data = json.loads(json.loads(extra_data_str))

                if matches['token'] not in extra_data:
                    continue

                value = extra_data.get(matches['token'])

                instances[name] = value
            except Exception:
                pass

        unresolved = list(filter(lambda x: x not in instances.keys(), unresolved))

        if len(unresolved):
            token_prefix = 'Token '
            authorization = request.headers.get('AUTHORIZATION', '')
            user_token = authorization[len(token_prefix):] if authorization.startswith(token_prefix) else None

            for item in get_secret_tokens(project, resource, settings.TOKEN, user_token):
                if item['name'] not in unresolved:
                    continue
                instances[item['name']] = item['value']

        for name in unresolved:
            if name not in instances:
                instances[name] = ''

        return instances

    def validate(self, attrs):
        if 'resource' in attrs:
            if 'project' not in attrs:
                raise ValidationError('"project" is required when specifying "resource"')

        if 'secret_tokens' in attrs and len(attrs['secret_tokens']):
            if 'resource' not in attrs:
                raise ValidationError('"resource" is required when specifying "secret_tokens"')
            names = attrs['secret_tokens'].split(',')

            attrs['secret_tokens'] = self.resolve_secret_tokens(names, attrs['project'], attrs['resource'])

        if isinstance(attrs['headers'], dict):
            attrs['headers'] = dict([[key, str(value)] for key, value in attrs['headers'].items()])

        return attrs

    def params_dict_to_list(self, items):
        return list(map(lambda x: {'name': x[0], 'value': x[1]}, items.items()))

    def interpolate(self, url, headers, query_params, body, pattern, replaces):
        def replace(str, replaces):
            for name, value in replaces.items():
                str = str.replace(pattern % name, value)
            return str

        url = replace(url, replaces)

        for header in headers:
            header['value'] = replace(header['value'], replaces)

        for query_param in query_params:
            query_param['value'] = replace(query_param['value'], replaces)

        if body:
            body = replace(body, replaces)

        return url, headers, query_params, body

    def submit(self):
        method = self.validated_data['method']
        url = self.validated_data['url']
        headers = self.validated_data['headers'] or []
        query_params = self.validated_data['query_params'] or []
        body = self.validated_data.get('body')

        if isinstance(headers, dict):
            headers = self.params_dict_to_list(headers)

        if isinstance(query_params, dict):
            query_params = self.params_dict_to_list(query_params)

        if 'secret_tokens' in self.validated_data:
            url, headers, query_params, body = self.interpolate(url, headers, query_params, body, '{-%s-}', self.validated_data['secret_tokens'])

        if 'context' in self.validated_data:
            url, headers, query_params, body = self.interpolate(url, headers, query_params, body, '{{%s}}', self.validated_data['context'])

        if body:
            body = body.encode('utf-8')

        headers = dict(map(lambda x: (x['name'], x['value']), headers))
        query_params = list(map(lambda x: (x['name'], x['value']), query_params))

        try:
            r = requests.request(method, url, headers=headers, params=query_params, data=body)
            response_headers = r.headers

            remove_headers = [
                'Access-Control-Allow-Origin',
                'Access-Control-Allow-Methods',
                'Access-Control-Allow-Headers',
                'Access-Control-Expose-Headers',
                'Connection',
                'Content-Encoding',
                'Content-Length',
                'Keep-Alive',
                'Proxy-Authenticate',
                'Proxy-Authorization',
                'TE',
                'Trailers',
                'Transfer-Encoding',
                'Upgrade'
            ]

            for header in remove_headers:
                if header in response_headers:
                    del response_headers[header]

            response = Response(data=r.content, status=r.status_code, headers=response_headers)

            return response
        except Exception as e:
            raise ValidationError(e)
