import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
import jwt
from django.conf import settings

logger = logging.getLogger(__name__)


class EmbeddingProgressConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time embedding progress updates"""
    
    async def connect(self):
        self.job_id = self.scope['url_route']['kwargs']['job_id']
        self.job_group_name = f'embedding_job_{self.job_id}'
        
        # Join job-specific group
        await self.channel_layer.group_add(
            self.job_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send initial connection message
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'job_id': self.job_id
        }))
        
        logger.info(f"WebSocket connected for job {self.job_id}")
    
    async def disconnect(self, close_code):
        # Leave job-specific group
        await self.channel_layer.group_discard(
            self.job_group_name,
            self.channel_name
        )
        
        logger.info(f"WebSocket disconnected for job {self.job_id}")
    
    async def receive(self, text_data):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(text_data)
            
            # Handle different message types
            if data.get('type') == 'ping':
                await self.send(text_data=json.dumps({
                    'type': 'pong'
                }))
        except Exception as e:
            logger.error(f"Error processing WebSocket message: {str(e)}")
    
    async def embedding_progress(self, event):
        """Handle embedding progress updates"""
        # Send progress update to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'progress_update',
            'job_id': event['job_id'],
            'status': event['status'],
            'message': event['message'],
            'progress': event.get('progress', {}),
            'timestamp': event.get('timestamp')
        }))
    
    async def embedding_complete(self, event):
        """Handle embedding completion"""
        await self.send(text_data=json.dumps({
            'type': 'job_complete',
            'job_id': event['job_id'],
            'status': 'completed',
            'message': event['message'],
            'chunks_count': event.get('chunks_count', 0),
            'timestamp': event.get('timestamp')
        }))
    
    async def embedding_error(self, event):
        """Handle embedding errors"""
        await self.send(text_data=json.dumps({
            'type': 'job_error',
            'job_id': event['job_id'],
            'status': 'error',
            'message': event['message'],
            'error': event.get('error'),
            'timestamp': event.get('timestamp')
        }))