from django.conf.urls import url

from jet_bridge_base.views.api import ApiView
from jet_bridge_base.views.external_auth.complete import ExternalAuthCompleteView
from jet_bridge_base.views.external_auth.login import ExternalAuthLoginView
from jet_bridge_base.views.file_upload import FileUploadView
from jet_bridge_base.views.graphql import GraphQLView
from jet_bridge_base.views.image_resize import ImageResizeView
from jet_bridge_base.views.message import MessageView
from jet_bridge_base.views.model import ModelViewSet
from jet_bridge_base.views.model_description import ModelDescriptionView
from jet_bridge_base.views.proxy_request import ProxyRequestView
from jet_bridge_base.views.register import RegisterView
from jet_bridge_base.views.reload import ReloadView
from jet_bridge_base.views.sql import SqlView
from jet_bridge_base.views.table import TableView
from jet_bridge_base.views.table_column import TableColumnView
from jet_django.route_view import route_view

from jet_django.router import Router

app_name = 'jet_django'


def init_urls():
    router = Router()

    router.register('models/(?P<model>[^/]+)/', route_view(ModelViewSet))
    router.register('tables/(?P<table>[^/]+)/columns/', route_view(TableColumnView))
    router.register('tables/', route_view(TableView))

    extra_urls = [
        url(r'^$', route_view(ApiView).as_view(), name='root'),
        url(r'^register/', route_view(RegisterView).as_view(), name='register'),
        url(r'^graphql/', route_view(GraphQLView).as_view(), name='graphql'),
        url(r'^model_descriptions/', route_view(ModelDescriptionView).as_view(), name='model-descriptions'),
        url(r'^sql/', route_view(SqlView).as_view(), name='sql'),
        url(r'^messages/', route_view(MessageView).as_view(), name='message'),
        url(r'^file_upload/', route_view(FileUploadView).as_view(), name='file-upload'),
        url(r'^image_resize/', route_view(ImageResizeView).as_view(), name='image-resize'),
        url(r'^reload/', route_view(ReloadView).as_view(), name='reload'),
        url(r'^proxy_request/', route_view(ProxyRequestView).as_view(), name='proxy-request'),
        url(r'^api/external_auth/login/(?P<app>[^/]+)/', route_view(ExternalAuthLoginView).as_view(), name='external-auth-login'),
        url(r'^api/external_auth/complete/(?P<app>[^/]+)/', route_view(ExternalAuthCompleteView).as_view(), name='external-auth-complete'),
    ]

    api_urls = router.urls + extra_urls

    return api_urls


jet_urls = init_urls()
urlpatterns = jet_urls
