"""WebSocket routing for OCR service"""
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/ocr/progress/(?P<job_id>[^/]+)/$', consumers.OCRProgressConsumer.as_asgi()),
]