"""WebSocket consumers for OCR progress monitoring"""
import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.conf import settings
from .auth import verify_websocket_token

logger = logging.getLogger(__name__)


class OCRProgressConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time OCR progress updates with authentication"""
    
    async def connect(self):
        """Handle WebSocket connection with authentication"""
        self.job_id = self.scope['url_route']['kwargs'].get('job_id')
        self.job_group_name = f'ocr_job_{self.job_id}'
        self.authenticated = False
        self.user_id = None
        
        # Don't accept connection yet - wait for authentication
        await self.accept()
        
        # Send authentication request
        await self.send(text_data=json.dumps({
            'type': 'auth_required',
            'message': 'Please authenticate with your JWT token'
        }))
        
        logger.info(f"WebSocket connection pending authentication for job {self.job_id}")
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        if self.authenticated:
            # Leave job-specific group
            await self.channel_layer.group_discard(
                self.job_group_name,
                self.channel_name
            )
            
            logger.info(f"WebSocket disconnected for job {self.job_id} (user: {self.user_id})")
        else:
            logger.info(f"Unauthenticated WebSocket disconnected for job {self.job_id}")
    
    async def receive(self, text_data):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            # Handle authentication
            if message_type == 'authenticate':
                await self.handle_authentication(data)
            
            # Only process other messages if authenticated
            elif self.authenticated:
                if message_type == 'ping':
                    await self.send(text_data=json.dumps({
                        'type': 'pong',
                        'timestamp': data.get('timestamp')
                    }))
                elif message_type == 'get_status':
                    await self.send_job_status()
            else:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Authentication required'
                }))
                
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON format'
            }))
        except Exception as e:
            logger.error(f"Error processing WebSocket message: {str(e)}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Failed to process message'
            }))
    
    async def handle_authentication(self, data):
        """Handle authentication message"""
        token = data.get('token')
        
        if not token:
            await self.send(text_data=json.dumps({
                'type': 'auth_failed',
                'message': 'Token required for authentication'
            }))
            return
        
        # Verify token
        payload, error = verify_websocket_token(token)
        
        if error:
            await self.send(text_data=json.dumps({
                'type': 'auth_failed',
                'message': error
            }))
            # Close connection after auth failure
            await self.close(code=4001)
            return
        
        # Authentication successful
        self.authenticated = True
        self.user_id = payload.get('user_id')
        
        # Join job-specific group
        await self.channel_layer.group_add(
            self.job_group_name,
            self.channel_name
        )
        
        # Send success message
        await self.send(text_data=json.dumps({
            'type': 'auth_success',
            'message': 'Authentication successful',
            'job_id': self.job_id,
            'user_id': self.user_id
        }))
        
        logger.info(f"WebSocket authenticated for job {self.job_id} (user: {self.user_id})")
        
        # Send initial job status
        await self.send_job_status()
    
    async def send_job_status(self):
        """Send current job status"""
        try:
            # Get job status from Redis
            from .queue_manager import RedisQueueManager
            queue_manager = RedisQueueManager()
            job = await database_sync_to_async(queue_manager.get_job)(self.job_id)
            
            if job:
                await self.send(text_data=json.dumps({
                    'type': 'status_update',
                    'job_id': self.job_id,
                    'status': job.get('status'),
                    'progress': job.get('progress', 0),
                    'message': job.get('message', ''),
                    'created_at': job.get('created_at'),
                    'started_at': job.get('started_at'),
                    'completed_at': job.get('completed_at')
                }))
            else:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Job not found'
                }))
                
        except Exception as e:
            logger.error(f"Failed to send job status: {str(e)}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Failed to retrieve job status'
            }))
    
    # Channel layer message handlers
    async def ocr_progress(self, event):
        """Handle OCR progress updates"""
        if self.authenticated:
            await self.send(text_data=json.dumps({
                'type': 'progress_update',
                'job_id': event['job_id'],
                'progress': event['progress'],
                'message': event['message'],
                'timestamp': event.get('timestamp')
            }))
    
    async def ocr_complete(self, event):
        """Handle OCR completion"""
        if self.authenticated:
            await self.send(text_data=json.dumps({
                'type': 'job_complete',
                'job_id': event['job_id'],
                'status': 'completed',
                'message': event['message'],
                'extracted_text_preview': event.get('text_preview', ''),
                'page_count': event.get('page_count', 0),
                'confidence': event.get('confidence', 0),
                'processing_time': event.get('processing_time', 0),
                'timestamp': event.get('timestamp')
            }))
    
    async def ocr_error(self, event):
        """Handle OCR errors"""
        if self.authenticated:
            await self.send(text_data=json.dumps({
                'type': 'job_error',
                'job_id': event['job_id'],
                'status': 'failed',
                'message': event['message'],
                'error': event.get('error'),
                'timestamp': event.get('timestamp')
            }))