from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/embedding/progress/(?P<job_id>[^/]+)/$', consumers.EmbeddingProgressConsumer.as_asgi()),
]