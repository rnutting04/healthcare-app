from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path("ws/translations/", consumers.TranslationConsumer.as_asgi()),
]