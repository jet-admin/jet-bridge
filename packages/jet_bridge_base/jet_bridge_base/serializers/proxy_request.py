import requests
from jet_bridge_base import fields, settings
from jet_bridge_base.exceptions.validation_error import ValidationError
from jet_bridge_base.responses.base import Response
from jet_bridge_base.serializers.serializer import Serializer
from jet_bridge_base.utils.backend import get_resource_secret_tokens


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

    def validate(self, attrs):
        if 'resource' in attrs:
            if 'project' not in attrs:
                raise ValidationError('"project" is required when specifying "resource"')

        if 'secret_tokens' in attrs and len(attrs['secret_tokens']):
            if 'resource' not in attrs:
                raise ValidationError('"resource" is required when specifying "secret_tokens"')
            names = attrs['secret_tokens'].split(',')
            instances = {}

            for item in get_resource_secret_tokens(attrs['project'], attrs['resource'], settings.TOKEN):
                instances[item['name']] = item

            for name in names:
                if name not in instances:
                    raise ValidationError('Secret token "{}" not found'.format(name))

            attrs['secret_tokens'] = instances.values()

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
            replaces = dict(
                filter(
                    lambda x: x[1] is not None,
                    map(lambda x: [x['name'], x['value']], self.validated_data['secret_tokens'])
                )
            )

            url, headers, query_params, body = self.interpolate(url, headers, query_params, body, '{-%s-}', replaces)

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
