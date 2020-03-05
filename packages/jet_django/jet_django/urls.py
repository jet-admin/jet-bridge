from django.conf.urls import url

from jet_bridge_base.views.api import ApiView
from jet_bridge_base.views.file_upload import FileUploadView
from jet_bridge_base.views.image_resize import ImageResizeView
from jet_bridge_base.views.message import MessageView
from jet_bridge_base.views.model import ModelViewSet
from jet_bridge_base.views.model_description import ModelDescriptionView
from jet_bridge_base.views.register import RegisterView
from jet_bridge_base.views.reload import ReloadView
from jet_bridge_base.views.sql import SqlView
from jet_django.route_view import route_view

from jet_django.router import Router

app_name = 'jet_django'


def init_urls():
    router = Router()

    router.register('models/(?P<model>[^/]+)/', route_view(ModelViewSet))

    extra_urls = [
        url(r'^$', route_view(ApiView).as_view(), name='root'),
        url(r'^register/', route_view(RegisterView).as_view(), name='register'),
        url(r'^model_descriptions/', route_view(ModelDescriptionView).as_view(), name='model-descriptions'),
        url(r'^sql/', route_view(SqlView).as_view(), name='sql'),
        url(r'^messages/', route_view(MessageView).as_view(), name='message'),
        url(r'^file_upload/', route_view(FileUploadView).as_view(), name='file-upload'),
        url(r'^image_resize/', route_view(ImageResizeView).as_view(), name='image-resize'),
        url(r'^reload/', route_view(ReloadView).as_view(), name='reload'),
    ]

    api_urls = router.urls + extra_urls

    return api_urls


jet_urls = init_urls()
urlpatterns = jet_urls
